import asyncio
from typing import List
import numpy as np


class EmbeddingService:
    """
    Converts text into numerical vectors (embeddings).

    Why embeddings?
      Plain text cannot be mathematically compared.
      Embeddings turn "Bonjour means hello" into a list of 384 numbers.
      Two semantically similar sentences produce similar vectors.
      This lets us find relevant content by meaning, not just keywords.

    Model: sentence-transformers/all-MiniLM-L6-v2
      - Free, runs locally, no API key
      - 384-dimensional vectors
      - Fast — ~2000 sentences/second on CPU
      - Downloads once (~90MB), cached automatically
    """

    def __init__(self):
        self._model = None  # lazy load on first use

    def _load_model(self):
        """Loads the sentence transformer model (once)."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print("[Embedder] Loading sentence-transformers model...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[Embedder] ✅ Model loaded")
        return self._model

    async def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Converts a list of text strings into embedding vectors.

        Args:
            texts — list of text strings to embed

        Returns:
            numpy array of shape (len(texts), 384)
            Each row is the embedding vector for one text.

        Runs in thread pool — sentence-transformers is synchronous.
        """
        if not texts:
            return np.array([])

        model = self._load_model()
        loop  = asyncio.get_event_loop()

        embeddings = await loop.run_in_executor(
            None,
            lambda: model.encode(
                texts,
                show_progress_bar = len(texts) > 10,
                batch_size        = 32,
                normalize_embeddings = True,  # normalize for cosine similarity
            )
        )
        return embeddings

    async def embed_single(self, text: str) -> np.ndarray:
        """
        Embeds a single text string.
        Used when embedding a user's query for RAG retrieval.

        Returns:
            1D numpy array of 384 floats.
        """
        result = await self.embed_texts([text])
        return result[0] if len(result) > 0 else np.zeros(384)

    def get_dimension(self) -> int:
        """Returns the embedding vector size (384 for MiniLM)."""
        return 384


# Single instance
embedding_service = EmbeddingService()