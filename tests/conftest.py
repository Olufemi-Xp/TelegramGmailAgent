import asyncio
import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database.models import Base, User, utc_now

# Use an in-memory SQLite database for test speed and isolation
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Initializes a clean, isolated database for each test function."""
    from app.database.session import engine
    from app.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Provides an active database session for unit tests."""
    from app.database.session import get_db_session
    async with get_db_session() as session:
        # Ensure default test user exists
        user = User(
            id=123456789,
            username="test_user",
            full_name="Test User",
            is_allowed=True,
            settings={},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(user)
        try:
            await session.commit()
        except Exception:
            await session.rollback()

    async with get_db_session() as session:
        yield session
