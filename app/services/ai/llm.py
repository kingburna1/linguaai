from typing import List, Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.config import settings


class LLMService:
    def __init__(self):
        self._models: Optional[List] = None

    def _build_models(self) -> List:
        if self._models is not None:
            return self._models

        # Use GEMINI_API_KEY only — never GOOGLE_API_KEY to avoid the warning
        gemini_key = settings.GEMINI_API_KEY
        groq_key   = settings.GROQ_API_KEY

        models = []

        if gemini_key:
            models.append(
                ChatGoogleGenerativeAI(
                    model          = settings.GEMINI_MODEL,
                    google_api_key = gemini_key,
                    temperature    = 0.7,
                )
            )

        if groq_key:
            models.append(
                ChatGroq(
                    model    = settings.GROQ_MODEL,
                    api_key  = groq_key,
                    temperature = 0.7,
                )
            )

        if not models:
            raise RuntimeError(
                "No LLM API keys configured. "
                "Set GEMINI_API_KEY and/or GROQ_API_KEY in your .env file."
            )

        self._models = models
        return self._models

    def _build_system_prompt(self, language_name: Optional[str] = None) -> str:
        """
        Builds the AI teacher system prompt.
        If a language name is provided, the AI focuses on teaching that language.
        """
        base = (
            "You are LinguaAI, a friendly and patient language learning tutor. "
            "You adapt your teaching style to the learner's age and level. "
            "For young children (under 8), use very simple words, short sentences, "
            "and a playful tone with emojis. "
            "For older learners, you can explain grammar rules, give examples, "
            "and correct mistakes gently. "
            "Always encourage the learner — never make them feel bad for mistakes. "
            "Keep responses concise and focused on language learning."
        )
        if language_name:
            base += (
                f" You are currently teaching {language_name}. "
                f"Focus all lessons and examples on {language_name}."
            )
        return base

    async def generate_reply(
        self,
        chat_history:  List[Dict[str, str]],
        user_message:  str,
        language_name: Optional[str] = None,
    ) -> str:
        """
        Sends the conversation to the LLM and returns the AI reply.

        Args:
            chat_history:  list of past messages [{"role": "user"|"ai", "content": "..."}]
            user_message:  the latest message from the user
            language_name: the language being learned (e.g. "French")

        Returns:
            AI reply as a string.

        Falls back from Gemini → Groq automatically if one fails.
        """
        models = self._build_models()

        # Build message list
        messages = [SystemMessage(content=self._build_system_prompt(language_name))]

        for msg in chat_history:
            role    = (msg.get("role") or "").lower()
            content = msg.get("content") or ""
            if not content:
                continue
            if role in {"ai", "assistant"}:
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=user_message))

        # Try each provider in order — first success wins
        errors: List[str] = []
        for model in models:
            try:
                response = await model.ainvoke(messages)
                return response.content
            except Exception as exc:
                provider = model.__class__.__name__
                errors.append(f"{provider}: {exc}")
                continue  # try next provider

        # All providers failed
        raise RuntimeError(
            "All configured LLM providers failed.\n" + "\n".join(errors)
        )



llm_service = LLMService()