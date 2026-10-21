from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User
from app.logging_config import get_logger

logger = get_logger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_or_create(self, user_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            user = User(
                id=user_id,
                username=username,
                full_name=full_name,
                is_allowed=True,
                settings={},
            )
            self.session.add(user)
            await self.session.flush()
            logger.info(f"Registered new user id={user_id} (@{username})")
        else:
            # Update username/full_name if changed
            if username and user.username != username:
                user.username = username
            if full_name and user.full_name != full_name:
                user.full_name = full_name
            await self.session.flush()
        return user
