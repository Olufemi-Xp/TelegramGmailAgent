from typing import List
from urllib.parse import urlparse
import httpx
from app.config import settings
from app.logging_config import get_logger
from app.providers.search.base import BaseSearchProvider, SearchResult

logger = get_logger(__name__)


class GoogleSearchProvider(BaseSearchProvider):
    name = "google"

    def __init__(self, api_key: str = "", engine_id: str = ""):
        self.api_key = api_key or settings.GOOGLE_SEARCH_API_KEY
        self.engine_id = engine_id or settings.GOOGLE_SEARCH_ENGINE_ID

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.api_key or not self.engine_id:
            raise ValueError("Google Search API key or Search Engine ID is not configured.")

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.engine_id,
            "q": query,
            "num": min(max_results, 10),
        }

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Google Search API error ({resp.status_code}): {resp.text}")
            data = resp.json()

        items = data.get("items", [])
        results: List[SearchResult] = []
        for i, item in enumerate(items):
            link = item.get("link", "")
            domain = urlparse(link).netloc
            results.append(
                SearchResult(
                    title=item.get("title", "No Title"),
                    url=link,
                    snippet=item.get("snippet", ""),
                    source_domain=domain,
                    score=1.0 - (i * 0.05),
                )
            )

        return results
