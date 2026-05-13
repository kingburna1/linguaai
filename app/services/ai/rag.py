from typing import List, Optional, Dict
from uuid import UUID

from app.services.content.embedder import embedding_service
from app.services.content.vector_store import vector_store
from app.services.content.scraper import content_scraper
from app.services.ai.llm import llm_service


class RAGService:
    """
    Retrieval-Augmented Generation pipeline.

    What RAG does:
      Instead of the AI making up answers from general training data,
      it first searches your actual indexed language content,
      then uses that content to ground its response.

    Pipeline:
      User message
        ↓
      Embed the message (convert to vector)
        ↓
      Search FAISS for similar content chunks
        ↓
      Build a prompt with: user message + retrieved chunks
        ↓
      Send to LLM → get grounded, accurate response
        ↓
      Return response + sources used

    Result: the AI teaches from YOUR content, not general knowledge.
    """

    async def retrieve(
        self,
        query:         str,
        language_code: str,
        top_k:         int = 4,
    ) -> List[dict]:
        """
        Finds the most relevant content chunks for a user's query.

        Args:
            query         — the user's message or question
            language_code — which language index to search
            top_k         — how many chunks to retrieve

        Returns list of relevant content chunks with scores.
        """
        # Embed the query
        query_embedding = await embedding_service.embed_single(query)

        # Search the vector store
        results = await vector_store.search(
            language_code    = language_code,
            query_embedding  = query_embedding,
            top_k            = top_k,
        )
        return results

    async def generate_with_context(
        self,
        user_message:  str,
        language_code: str,
        language_name: str,
        chat_history:  List[Dict[str, str]],
        user_age:      Optional[int] = None,
        top_k:         int = 4,
    ) -> dict:
        """
        Full RAG pipeline — retrieves context then generates a response.

        Args:
            user_message  — what the user said
            language_code — e.g. "fr", "yo"
            language_name — e.g. "French", "Yoruba"
            chat_history  — previous messages for context
            user_age      — user age for complexity adaptation
            top_k         — chunks to retrieve

        Returns dict:
            {
                "reply":    "AI's teaching response",
                "sources":  [...],   ← content used (for transparency)
                "used_rag": True     ← whether RAG content was found
            }
        """
        # 1. Retrieve relevant content
        chunks = await self.retrieve(user_message, language_code, top_k)

        # 2. Build context from retrieved chunks
        context = self._build_context(chunks)

        # 3. Build RAG-enhanced system prompt
        system_prompt = self._build_rag_prompt(
            language_name = language_name,
            context       = context,
            user_age      = user_age,
            has_content   = bool(chunks),
        )

        # 4. Generate response with context
        messages_with_system = [
            {"role": "system", "content": system_prompt}
        ] + chat_history

        reply = await llm_service.generate_reply(
            chat_history  = messages_with_system,
            user_message  = user_message,
            language_name = language_name,
        )

        return {
            "reply":    reply,
            "sources":  [
                {
                    "title":       c.get("title", ""),
                    "source_type": c.get("source_type", ""),
                    "source_url":  c.get("source_url", ""),
                    "score":       round(c.get("score", 0), 3),
                }
                for c in chunks
            ],
            "used_rag": bool(chunks),
        }

    def _build_context(self, chunks: List[dict]) -> str:
        """Formats retrieved chunks into a context string for the prompt."""
        if not chunks:
            return ""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("title") or chunk.get("source_type", "Source")
            parts.append(f"[Source {i} — {source}]\n{chunk['text']}")
        return "\n\n".join(parts)

    def _build_rag_prompt(
        self,
        language_name: str,
        context:       str,
        user_age:      Optional[int],
        has_content:   bool,
    ) -> str:
        """
        Builds the system prompt that tells the AI how to use the context.
        Adapts language complexity based on user age.
        """
        # Age-based complexity
        if user_age is not None:
            if user_age <= 5:
                age_instruction = (
                    "The learner is a very young child (age 5 or under). "
                    "Use extremely simple words, short sentences, lots of emojis, "
                    "and a very playful, encouraging tone. "
                    "Introduce only one word or phrase at a time."
                )
            elif user_age <= 10:
                age_instruction = (
                    "The learner is a child (age 6-10). "
                    "Use simple vocabulary, short sentences, and a fun friendly tone. "
                    "Use emojis occasionally. Give simple examples."
                )
            elif user_age <= 17:
                age_instruction = (
                    "The learner is a teenager (age 11-17). "
                    "Use clear language with some grammar explanations. "
                    "Keep it engaging and relatable."
                )
            else:
                age_instruction = (
                    "The learner is an adult. "
                    "You can use proper linguistic terminology, "
                    "explain grammar rules in detail, and give rich examples."
                )
        else:
            age_instruction = "Adapt your language to match the learner's apparent level."

        # Base prompt
        prompt = f"""You are LinguaAI, an expert {language_name} language tutor.
Your job is to teach {language_name} effectively and make learning enjoyable.

{age_instruction}

Teaching guidelines:
- Always encourage the learner — mistakes are part of learning
- Give pronunciation hints where helpful (use phonetic spelling)
- Provide example sentences when teaching vocabulary
- Correct errors gently and explain why
- Keep responses focused and not too long
"""

        # Add RAG context if available
        if has_content and context:
            prompt += f"""
You have access to the following {language_name} learning content.
Use it to ground your teaching in real, accurate information:

--- LANGUAGE CONTENT ---
{context}
--- END CONTENT ---

Base your teaching on this content where relevant.
If the user asks something not covered by the content, use your knowledge
but note that you are speaking from general knowledge.
"""
        else:
            prompt += f"""
No specific content has been indexed for {language_name} yet.
Teach from your general knowledge about {language_name}.
Encourage the admin to index content for more accurate teaching.
"""

        return prompt

    # ── INDEXING PIPELINE ─────────────────────────────────────────────────────

    async def index_language(
        self,
        language_id:   UUID,
        language_name: str,
        language_code: str,
        youtube_ids:   List[str] = None,
        wiki_topics:   List[str] = None,
        extra_urls:    List[str] = None,
        db=None,
    ) -> dict:
        """
        Full indexing pipeline for a new language.
        Called when an admin triggers content scraping.

        Flow:
          1. Scrape content from YouTube, Wikipedia, URLs
          2. Split into chunks
          3. Embed all chunks
          4. Store in FAISS
          5. Save chunks to PostgreSQL for browsing
          6. Mark language as available

        Returns summary of what was indexed.
        """
        from app.crud.crud_language import crud_language

        print(f"[RAG] Starting indexing for {language_name} ({language_code})")

        # 1. Scrape content
        scraped = await content_scraper.scrape_language_content(
            language_name = language_name,
            language_code = language_code,
            youtube_ids   = youtube_ids,
            wiki_topics   = wiki_topics,
            extra_urls    = extra_urls,
        )

        if not scraped:
            return {"success": False, "message": "No content scraped", "chunks": 0}

        total_chunks = 0

        for source in scraped:
            chunks  = source.get("chunks", [])
            if not chunks:
                continue

            # 2. Embed chunks
            embeddings = await embedding_service.embed_texts(chunks)

            # 3. Build metadata list
            meta = [
                {
                    "source_url":  source.get("source_url", ""),
                    "source_type": source.get("source_type", ""),
                    "title":       source.get("title", ""),
                }
                for _ in chunks
            ]

            # 4. Store in FAISS
            added = await vector_store.add_chunks(
                language_code = language_code,
                chunks        = chunks,
                embeddings    = embeddings,
                metadata      = meta,
            )
            total_chunks += added

            # 5. Save chunks to PostgreSQL (if db provided)
            if db:
                for chunk, m in zip(chunks, meta):
                    await crud_language.add_content(
                        db,
                        language_id  = language_id,
                        source_url   = m["source_url"],
                        source_type  = m["source_type"],
                        title        = m["title"],
                        content      = chunk,
                    )

        # 6. Mark language as available
        if db:
            lang = await crud_language.get(db, language_id)
            if lang:
                await crud_language.mark_available(db, lang)
                await db.commit()

        print(f"[RAG] ✅ Indexed {total_chunks} chunks for {language_name}")
        return {
            "success":       True,
            "language":      language_name,
            "total_chunks":  total_chunks,
            "sources_count": len(scraped),
        }


# Single instance
rag_service = RAGService()