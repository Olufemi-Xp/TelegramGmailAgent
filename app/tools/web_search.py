import time
from typing import Any, Dict, List
from app.logging_config import get_logger
from app.providers.search.base import SearchResult
from app.providers.search.google import GoogleSearchProvider
from app.providers.search.perplexity import PerplexitySearchProvider
from app.providers.search.tavily import TavilySearchProvider

logger = get_logger(__name__)

# Simple in-memory cache: query -> (timestamp, List[SearchResult])
SEARCH_CACHE: Dict[str, tuple[float, List[SearchResult]]] = {}
CACHE_TTL_SECONDS = 600  # 10 minutes


class WebSearchCoordinator:
    def __init__(self):
        self.providers = [
            TavilySearchProvider(),
            PerplexitySearchProvider(),
            GoogleSearchProvider(),
        ]

    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        cache_key = query.strip().lower()
        now = time.time()
        if cache_key in SEARCH_CACHE:
            ts, cached_results = SEARCH_CACHE[cache_key]
            if now - ts < CACHE_TTL_SECONDS:
                logger.debug(f"Serving cached web search for: '{query}'")
                return {
                    "query": query,
                    "results": [r.model_dump() for r in cached_results],
                    "cached": True,
                }

        errors = []
        for provider in self.providers:
            try:
                results = await provider.search(query, max_results=max_results)
                if results:
                    SEARCH_CACHE[cache_key] = (now, results)
                    return {
                        "query": query,
                        "provider": provider.name,
                        "results": [r.model_dump() for r in results],
                        "cached": False,
                    }
            except Exception as e:
                err_msg = f"{provider.name}: {str(e)}"
                logger.debug(f"Search provider failed: {err_msg}")
                errors.append(err_msg)

        return {
            "query": query,
            "results": [],
            "error": f"All search providers failed or returned no results. Details: {'; '.join(errors)}",
        }


web_search_tool = WebSearchCoordinator()
