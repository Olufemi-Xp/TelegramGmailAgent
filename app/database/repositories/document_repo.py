import math
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Document, DocumentChunk
from app.logging_config import get_logger

logger = get_logger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self,
        user_id: int,
        filename: str,
        file_type: str,
        file_size_bytes: int,
        storage_path: str,
        page_count: int = 1,
    ) -> Document:
        doc = Document(
            id=str(uuid.uuid4()),
            user_id=user_id,
            filename=filename,
            file_type=file_type.lower(),
            file_size_bytes=file_size_bytes,
            storage_path=storage_path,
            page_count=page_count,
            chunk_count=0,
            is_indexed=False,
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def add_chunks(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
    ) -> int:
        count = 0
        for i, chunk_data in enumerate(chunks):
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document_id,
                chunk_index=i,
                content=chunk_data["content"],
                metadata_json=chunk_data.get("metadata", {}),
                embedding=chunk_data.get("embedding"),
            )
            self.session.add(chunk)
            count += 1
        
        # Update document chunk count and indexed state
        stmt = select(Document).where(Document.id == document_id)
        res = await self.session.execute(stmt)
        doc = res.scalars().first()
        if doc:
            doc.chunk_count = count
            doc.is_indexed = True

        await self.session.flush()
        return count

    async def list_documents(self, user_id: int) -> List[Document]:
        stmt = select(Document).where(Document.user_id == user_id).order_by(desc(Document.created_at))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_document(self, document_id: str, user_id: int) -> Optional[Document]:
        stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def delete_document(self, document_id: str, user_id: int) -> bool:
        stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
        result = await self.session.execute(stmt)
        doc = result.scalars().first()
        if not doc:
            return False

        # Cascade deletes chunks automatically
        await self.session.delete(doc)
        await self.session.flush()
        logger.info(f"Deleted document id={document_id} and all related chunks for user={user_id}")
        return True

    async def search_chunks_by_embedding(
        self,
        user_id: int,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> List[Tuple[DocumentChunk, float, str]]:
        """Finds most relevant document chunks for the user using vector similarity.
        Returns list of (DocumentChunk, similarity_score, document_filename).
        """
        # Fetch candidate chunks joined with documents for this user
        query = (
            select(DocumentChunk, Document.filename)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.user_id == user_id)
        )
        if document_id:
            query = query.where(Document.id == document_id)

        result = await self.session.execute(query)
        rows = result.all()

        scored_chunks = []
        for chunk, filename in rows:
            if chunk.embedding is not None:
                # Calculate similarity
                sim = cosine_similarity(query_embedding, chunk.embedding)
                scored_chunks.append((chunk, sim, filename))

        # Sort descending by similarity
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]
