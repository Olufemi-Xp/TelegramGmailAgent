from typing import Any, Dict, List, Optional
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.memory_repo import MemoryRepository
from app.database.session import get_db_session
from app.logging_config import get_logger
from app.providers.embeddings.provider import embedding_service

logger = get_logger(__name__)


class MemoryRetriever:
    @staticmethod
    async def get_relevant_context(
        user_id: int,
        query: str,
        top_chunks: int = 3,
        top_facts: int = 5,
    ) -> Dict[str, Any]:
        """Retrieves personal memories and semantically matched document excerpts."""
        query_embedding = await embedding_service.get_embedding(query)

        facts: List[Dict[str, Any]] = []
        doc_chunks: List[Dict[str, Any]] = []

        async with get_db_session() as session:
            # 1. Retrieve personal fact memories
            mem_repo = MemoryRepository(session)
            matching_facts = await mem_repo.search_memories(user_id=user_id, query=query, limit=top_facts)
            if not matching_facts:
                # If specific query didn't match keyword, fetch top recent general facts
                matching_facts = await mem_repo.list_memories(user_id=user_id, limit=top_facts)

            for mf in matching_facts:
                facts.append({
                    "id": mf.id,
                    "category": mf.category,
                    "content": mf.content,
                })

            # 2. Retrieve document chunks using semantic vector similarity
            doc_repo = DocumentRepository(session)
            scored = await doc_repo.search_chunks_by_embedding(
                user_id=user_id,
                query_embedding=query_embedding,
                top_k=top_chunks,
            )
            for chunk, score, filename in scored:
                # Only include chunks with positive similarity threshold
                if score > 0.15:
                    doc_chunks.append({
                        "document": filename,
                        "content": chunk.content,
                        "score": round(score, 3),
                    })

        return {
            "personal_facts": facts,
            "document_excerpts": doc_chunks,
        }
