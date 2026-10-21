from typing import List
from urllib.parse import urlparse
import httpx
from app.config import settings
from app.logging_config import get_logger
from app.providers.search.base import BaseSearchProvider, SearchResult

logger = get_logger(__name__)


class TavilySearchProvider(BaseSearchProvider):
    name = "tavily"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.TAVILY_API_KEY

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.api_key:
            raise ValueError("Tavily API key is not configured.")

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
        }

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Tavily API error ({resp.status_code}): {resp.text}")
            data = resp.json()

        raw_results = data.get("results", [])
        results: List[SearchResult] = []
        for item in raw_results:
            link = item.get("url", "")
            domain = urlparse(link).netloc
            results.append(
                SearchResult(
                    title=item.get("title", "No Title"),
                    url=link,
                    snippet=item.get("content", ""),
                    source_domain=domain,
                    published_date=item.get("published_date"),
                    score=float(item.get("score", 1.0)),
                )
            )

        return results
