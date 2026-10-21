import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from app.database.repositories.job_repo import JobRepository
from app.database.session import get_db_session
from app.logging_config import get_logger
from app.providers.search.base import SearchResult
from app.providers.search.tavily import TavilySearchProvider
from app.providers.search.perplexity import PerplexitySearchProvider
from app.providers.search.google import GoogleSearchProvider

logger = get_logger(__name__)


class JobDiscoveryService:
    def __init__(self):
        self.tavily = TavilySearchProvider()
        self.perplexity = PerplexitySearchProvider()
        self.google = GoogleSearchProvider()

    async def _execute_search(self, query: str) -> List[SearchResult]:
        # Try Tavily first, then Perplexity, then Google
        providers = [self.tavily, self.perplexity, self.google]
        for p in providers:
            try:
                results = await p.search(query, max_results=6)
                if results:
                    return results
            except Exception as e:
                logger.debug(f"Search provider {p.name} failed for job query: {e}")
                continue
        return []

    async def find_opportunities(
        self,
        user_id: int,
        query: str,
        work_arrangement: str = "remote",
        location: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Discovers job or freelance opportunities and deduplicates against the database."""
        search_terms = f"{query} hiring {work_arrangement}"
        if location:
            search_terms += f" {location}"
        if keywords:
            search_terms += f" {keywords}"

        raw_results = await self._execute_search(search_terms)
        new_jobs: List[Dict[str, Any]] = []

        async with get_db_session() as session:
            repo = JobRepository(session)
            for item in raw_results:
                domain = item.source_domain or urlparse(item.url).netloc
                # Simple extraction heuristic for employer
                employer = domain.replace("www.", "").split(".")[0].capitalize()
                
                job = await repo.save_job(
                    user_id=user_id,
                    title=item.title,
                    source_link=item.url,
                    source_domain=domain,
                    employer=employer,
                    location=location or "Remote",
                    work_arrangement=work_arrangement,
                    date_posted=item.published_date,
                    summary=item.snippet[:400],
                    match_rationale=f"Matched search query: {query}",
                )
                if job:
                    new_jobs.append({
                        "id": job.id,
                        "title": job.title,
                        "employer": job.employer,
                        "url": job.source_link,
                        "location": job.location,
                        "summary": job.summary,
                    })

        return new_jobs


job_service = JobDiscoveryService()
