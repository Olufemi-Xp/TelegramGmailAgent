from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source_domain: str = ""
    published_date: Optional[str] = None
    score: float = 1.0


class BaseSearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        pass
