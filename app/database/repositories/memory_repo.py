import uuid
from typing import Dict, List, Optional
from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import PersonalMemory
from app.logging_config import get_logger

logger = get_logger(__name__)


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_memory(
        self,
        user_id: int,
        content: str,
        category: str = "general",
        confidence: float = 1.0,
        verification_state: str = "verified",
        source: str = "user_instruction",
    ) -> PersonalMemory:
        mem = PersonalMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            category=category.lower(),
            content=content.strip(),
            confidence=confidence,
            verification_state=verification_state,
            source=source,
        )
        self.session.add(mem)
        await self.session.flush()
        logger.info(f"Saved memory for user {user_id} in category '{category}': {content[:50]}...")
        return mem

    async def list_memories(self, user_id: int, category: Optional[str] = None, limit: int = 50) -> List[PersonalMemory]:
        stmt = select(PersonalMemory).where(PersonalMemory.user_id == user_id)
        if category and category.lower() != "all":
            stmt = stmt.where(PersonalMemory.category == category.lower())
        stmt = stmt.order_by(desc(PersonalMemory.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_memories(self, user_id: int, query: str, limit: int = 10) -> List[PersonalMemory]:
        search_pattern = f"%{query}%"
        stmt = (
            select(PersonalMemory)
            .where(
                PersonalMemory.user_id == user_id,
                or_(
                    PersonalMemory.content.ilike(search_pattern),
                    PersonalMemory.category.ilike(search_pattern),
                ),
            )
            .order_by(desc(PersonalMemory.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, memory_id: str, user_id: int) -> Optional[PersonalMemory]:
        stmt = select(PersonalMemory).where(PersonalMemory.id == memory_id, PersonalMemory.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def delete_memory(self, memory_id: str, user_id: int) -> bool:
        stmt = delete(PersonalMemory).where(PersonalMemory.id == memory_id, PersonalMemory.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def get_category_counts(self, user_id: int) -> Dict[str, int]:
        stmt = (
            select(PersonalMemory.category, func.count(PersonalMemory.id))
            .where(PersonalMemory.user_id == user_id)
            .group_by(PersonalMemory.category)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
