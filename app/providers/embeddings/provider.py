import hashlib
import math
from typing import List
import httpx
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def generate_fallback_embedding(text: str, dim: int = 384) -> List[float]:
    """Generates a normalized deterministic dense embedding vector from text.
    Ensures tests and lightweight deployments run without heavy torch/cuda downloads.
    """
    vector = [0.0] * dim
    words = text.lower().split()
    if not words:
        return vector

    for i, word in enumerate(words):
        # Generate hash for the token
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        weight = 1.0 / (1.0 + 0.1 * i)
        vector[idx] += sign * weight

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]

    return vector


class EmbeddingService:
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER.lower()
        self.dim = settings.EMBEDDING_DIMENSION

    async def get_embedding(self, text: str) -> List[float]:
        """Returns embedding vector for input text."""
        if not text.strip():
            return [0.0] * self.dim

        if self.provider == "openrouter" or self.provider == "openai":
            try:
                url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/embeddings"
                headers = {
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": settings.EMBEDDING_MODEL,
                    "input": text,
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        emb = data["data"][0]["embedding"]
                        return emb[: self.dim]
            except Exception as e:
                logger.warning(f"Remote embedding request failed: {e}. Using local fallback vector.")

        # Local deterministic vectorizer
        return generate_fallback_embedding(text, dim=self.dim)

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        results = []
        for t in texts:
            emb = await self.get_embedding(t)
            results.append(emb)
        return results


embedding_service = EmbeddingService()
