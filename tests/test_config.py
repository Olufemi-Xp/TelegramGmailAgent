import pytest
from app.config import Settings


def test_allowed_user_ids_parsing():
    s1 = Settings(TELEGRAM_ALLOWED_USER_IDS="123, 456, 789")
    assert s1.TELEGRAM_ALLOWED_USER_IDS == [123, 456, 789]

    s2 = Settings(TELEGRAM_ALLOWED_USER_IDS=[999, 888])
    assert s2.TELEGRAM_ALLOWED_USER_IDS == [999, 888]

    s3 = Settings(TELEGRAM_ALLOWED_USER_IDS="")
    assert s3.TELEGRAM_ALLOWED_USER_IDS == []


def test_settings_properties():
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
        GOOGLE_CLIENT_ID="id",
        GOOGLE_CLIENT_SECRET="secret",
        PERPLEXITY_API_KEY="key",
    )
    assert s.is_postgres is True
    assert s.has_gmail_configured is True
    assert s.has_search_configured is True
