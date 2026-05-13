import os
import json
import asyncio
import numpy as np
from typing import List, Optional
from pathlib import Path


class VectorStore:
    """
    FAISS-based vector store for language content retrieval.

    What FAISS does:
      Stores millions of embedding vectors and finds the most
      similar ones to a query vector in milliseconds.
      Think of it as a search engine that understands meaning.

    Storage structure:
      Each language gets its own FAISS index file on disk:
        vector_store/
          fr.index      ← French embeddings
          fr_meta.json  ← French chunk metadata (text + source)
          yo.index      ← Yoruba embeddings
          yo_meta.json  ← Yoruba metadata
          ...

    Why separate per language?
      Faster search — only search the relevant language.
      Easier to update — re-index one language without touching others.
    """

    def __init__(self, store_dir: str = "vector_store"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(exist_ok=True)
        self._indexes  = {}   # in-memory cache: {lang_code: faiss.Index}
        self._metadata = {}   # in-memory cache: {lang_code: [{"text":..., "source":...}]}

    # ── ADD CONTENT ───────────────────────────────────────────────────────────

    async def add_chunks(
        self,
        language_code: str,
        chunks:        List[str],
        embeddings:    np.ndarray,
        metadata:      List[dict],
    ) -> int:
        """
        Adds content chunks and their embeddings to the language index.

        Args:
            language_code — e.g. "fr", "yo", "sw"
            chunks        — list of text strings
            embeddings    — numpy array shape (len(chunks), 384)
            metadata      — list of dicts with source info per chunk:
                            [{"source_url": "...", "source_type": "youtube", "title": "..."}]

        Returns:
            Number of chunks added.
        """
        import faiss

        if len(chunks) == 0:
            return 0

        # Load or create index for this language
        index = await self._get_or_create_index(language_code, embeddings.shape[1])
        meta  = self._metadata.get(language_code, [])

        # Convert to float32 — FAISS requirement
        vecs = embeddings.astype(np.float32)

        # Add to FAISS index
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: index.add(vecs))

        # Store metadata alongside each chunk
        for i, chunk in enumerate(chunks):
            meta.append({
                "text":        chunk,
                "source_url":  metadata[i].get("source_url", ""),
                "source_type": metadata[i].get("source_type", ""),
                "title":       metadata[i].get("title", ""),
            })

        self._indexes[language_code]  = index
        self._metadata[language_code] = meta

        # Persist to disk
        await self._save(language_code)

        return len(chunks)

    # ── SEARCH ────────────────────────────────────────────────────────────────

    async def search(
        self,
        language_code:  str,
        query_embedding: np.ndarray,
        top_k:          int = 5,
    ) -> List[dict]:
        """
        Finds the top-k most relevant chunks for a query.

        Args:
            language_code    — which language index to search
            query_embedding  — the embedded query vector (384 floats)
            top_k            — how many results to return

        Returns list of dicts:
            [
                {
                    "text":        "Bonjour means hello in French...",
                    "source_url":  "https://...",
                    "source_type": "wikipedia",
                    "title":       "French language",
                    "score":       0.92,   ← similarity score (0-1)
                },
                ...
            ]
        """
        import faiss

        index = await self._load_index(language_code)
        if index is None or index.ntotal == 0:
            return []

        meta = self._metadata.get(language_code, [])
        if not meta:
            return []

        # Search FAISS
        query_vec = query_embedding.astype(np.float32).reshape(1, -1)
        k         = min(top_k, index.ntotal)

        loop              = asyncio.get_event_loop()
        distances, indices = await loop.run_in_executor(
            None, lambda: index.search(query_vec, k)
        )

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(meta):
                continue
            chunk = meta[idx].copy()
            chunk["score"] = float(dist)  # cosine similarity (higher = better)
            results.append(chunk)

        return results

    async def get_chunk_count(self, language_code: str) -> int:
        """Returns how many chunks are indexed for a language."""
        index = await self._load_index(language_code)
        return index.ntotal if index else 0

    async def clear_language(self, language_code: str) -> None:
        """Deletes all indexed content for a language. Used when re-indexing."""
        import faiss
        dim   = 384
        index = faiss.IndexFlatIP(dim)
        self._indexes[language_code]  = index
        self._metadata[language_code] = []
        await self._save(language_code)
        print(f"[VectorStore] Cleared index for: {language_code}")

    # ── PERSISTENCE ───────────────────────────────────────────────────────────

    async def _get_or_create_index(self, language_code: str, dim: int):
        """Returns existing index or creates a new one."""
        import faiss
        if language_code in self._indexes:
            return self._indexes[language_code]
        index = await self._load_index(language_code)
        if index is None:
            # IndexFlatIP = cosine similarity (with normalized vectors)
            index = faiss.IndexFlatIP(dim)
        self._indexes[language_code] = index
        return index

    async def _load_index(self, language_code: str):
        """Loads a FAISS index from disk if not already in memory."""
        import faiss
        if language_code in self._indexes:
            return self._indexes[language_code]

        index_path = self.store_dir / f"{language_code}.index"
        meta_path  = self.store_dir / f"{language_code}_meta.json"

        if not index_path.exists():
            return None

        loop  = asyncio.get_event_loop()
        index = await loop.run_in_executor(
            None, lambda: faiss.read_index(str(index_path))
        )
        self._indexes[language_code] = index

        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                self._metadata[language_code] = json.load(f)

        print(f"[VectorStore] Loaded index for '{language_code}': {index.ntotal} chunks")
        return index

    async def _save(self, language_code: str) -> None:
        """Saves FAISS index and metadata to disk."""
        import faiss
        index      = self._indexes.get(language_code)
        meta       = self._metadata.get(language_code, [])
        index_path = self.store_dir / f"{language_code}.index"
        meta_path  = self.store_dir / f"{language_code}_meta.json"

        if index:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: faiss.write_index(index, str(index_path))
            )

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"[VectorStore] Saved '{language_code}': {len(meta)} chunks on disk")


# Single instance — shared across the app
vector_store = VectorStore()