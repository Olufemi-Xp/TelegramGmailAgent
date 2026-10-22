import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database.models import Base
from app.logging_config import get_logger

from sqlalchemy.pool import NullPool

logger = get_logger(__name__)

is_serverless = bool(os.getenv("VERCEL") or settings.is_webhook_mode)

# Normalize sqlite URL to ensure directory exists or redirect to /tmp in serverless
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite+aiosqlite:///"):
    if is_serverless:
        # Vercel filesystem is read-only except /tmp
        db_url = "sqlite+aiosqlite:////tmp/agent.db"
    else:
        path = db_url.replace("sqlite+aiosqlite:///", "")
        dir_name = os.path.dirname(path)
        if dir_name:
            try:
                os.makedirs(dir_name, exist_ok=True)
            except Exception:
                pass

engine_kwargs = {
    "echo": settings.DB_ECHO,
    "future": True,
}
if not settings.is_postgres:
    engine_kwargs["connect_args"] = {"timeout": 30}
else:
    engine_kwargs["pool_pre_ping"] = True
    if is_serverless:
        # Prevent connection pooling leaks in ephemeral serverless function instances
        engine_kwargs["poolclass"] = NullPool

engine: AsyncEngine = create_async_engine(
    db_url,
    **engine_kwargs,
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency / context manager yielding an active async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initializes the database schema and pgvector extension if on PostgreSQL."""
    async with engine.begin() as conn:
        if settings.is_postgres:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                logger.info("pgvector extension verified or created.")
            except Exception as e:
                logger.warning(f"Could not initialize pgvector extension: {e}. Falling back to standard JSON vectors.")
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")


async def check_db_health() -> bool:
    """Executes a simple probe query to verify database connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
