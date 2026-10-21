from typing import Any, Dict, List, Optional
from app.database.repositories.conversation_repo import ConversationRepository
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.memory_repo import MemoryRepository
from app.database.session import get_db_session
from app.logging_config import get_logger
from app.memory.indexing import DocumentIndexer

logger = get_logger(__name__)


class MemoryService:
    @staticmethod
    async def save_fact(user_id: int, content: str, category: str = "general") -> Dict[str, Any]:
        async with get_db_session() as session:
            repo = MemoryRepository(session)
            mem = await repo.add_memory(user_id=user_id, content=content, category=category)
            return {
                "id": mem.id,
                "category": mem.category,
                "content": mem.content,
                "created_at": mem.created_at.isoformat(),
            }

    @staticmethod
    async def delete_fact(user_id: int, memory_id: str) -> bool:
        async with get_db_session() as session:
            repo = MemoryRepository(session)
            return await repo.delete_memory(memory_id=memory_id, user_id=user_id)

    @staticmethod
    async def get_memory_stats(user_id: int) -> Dict[str, Any]:
        async with get_db_session() as session:
            mem_repo = MemoryRepository(session)
            doc_repo = DocumentRepository(session)
            cat_counts = await mem_repo.get_category_counts(user_id)
            total_facts = sum(cat_counts.values())
            docs = await doc_repo.list_documents(user_id)
            return {
                "total_facts": total_facts,
                "category_breakdown": cat_counts,
                "total_documents": len(docs),
                "documents": [{"id": d.id, "filename": d.filename, "chunks": d.chunk_count} for d in docs],
            }

    @staticmethod
    async def list_documents(user_id: int) -> List[Dict[str, Any]]:
        async with get_db_session() as session:
            doc_repo = DocumentRepository(session)
            docs = await doc_repo.list_documents(user_id)
            return [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "file_type": d.file_type,
                    "size_kb": round(d.file_size_bytes / 1024, 1),
                    "chunk_count": d.chunk_count,
                    "is_indexed": d.is_indexed,
                }
                for d in docs
            ]

    @staticmethod
    async def delete_document(user_id: int, document_id: str) -> bool:
        async with get_db_session() as session:
            doc_repo = DocumentRepository(session)
            return await doc_repo.delete_document(document_id=document_id, user_id=user_id)

    @staticmethod
    async def index_file(user_id: int, file_path: str, filename: str) -> Dict[str, Any]:
        return await DocumentIndexer.index_file(user_id=user_id, file_path=file_path, original_filename=filename)

    @staticmethod
    async def clear_summary(user_id: int) -> bool:
        async with get_db_session() as session:
            conv_repo = ConversationRepository(session)
            conv = await conv_repo.get_or_create_active_conversation(user_id)
            deleted = await conv_repo.clear_summaries(conv.id)
            return deleted > 0


memory_service = MemoryService()
