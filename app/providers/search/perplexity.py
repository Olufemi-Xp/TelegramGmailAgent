from typing import List
from urllib.parse import urlparse
import httpx
from app.config import settings
from app.logging_config import get_logger
from app.providers.search.base import BaseSearchProvider, SearchResult

logger = get_logger(__name__)


class PerplexitySearchProvider(BaseSearchProvider):
    name = "perplexity"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.PERPLEXITY_API_KEY
        self.model = settings.PERPLEXITY_MODEL

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.api_key:
            raise ValueError("Perplexity API key is not configured.")

        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise web research assistant. Provide concise, fact-backed summaries with exact sources.",
                },
                {"role": "user", "content": query},
            ],
        }

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Perplexity API error ({resp.status_code}): {resp.text}")
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        citations = data.get("citations", [])

        results: List[SearchResult] = []
        if citations:
            for i, citation_url in enumerate(citations[:max_results]):
                domain = urlparse(citation_url).netloc
                results.append(
                    SearchResult(
                        title=f"Source {i+1}: {domain}",
                        url=citation_url,
                        snippet=content[:300] if i == 0 else f"Referenced source {citation_url}",
                        source_domain=domain,
                        score=1.0 - (i * 0.05),
                    )
                )
        elif content:
            # If no explicit citations array, return synthesized answer
            results.append(
                SearchResult(
                    title=f"Perplexity Research: {query[:40]}",
                    url="https://perplexity.ai",
                    snippet=content[:500],
                    source_domain="perplexity.ai",
                    score=1.0,
                )
            )

        return results
