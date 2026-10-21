from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import Message, User as TgUser, Update
from app.bot.formatting import split_message
from app.bot.middleware import SecurityMiddleware
from app.config import settings


def test_message_splitting_under_limit():
    short_text = "Hello world"
    chunks = split_message(short_text, max_length=100)
    assert len(chunks) == 1
    assert chunks[0] == "Hello world"


def test_message_splitting_over_limit():
    long_text = "\n".join(f"Line {i}: This is some long message content to test chunking." for i in range(100))
    chunks = split_message(long_text, max_length=500)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


@pytest.mark.asyncio
async def test_middleware_blocks_unauthorized_user():
    middleware = SecurityMiddleware()
    settings.TELEGRAM_ALLOWED_USER_IDS = [111111]

    # Mock event from unauthorized user
    mock_user = MagicMock(spec=TgUser)
    mock_user.id = 999999
    mock_user.username = "intruder"

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.answer = AsyncMock()

    mock_handler = AsyncMock()

    await middleware(
        handler=mock_handler,
        event=mock_msg,
        data={"event_from_user": mock_user},
    )

    # Handler should NOT be called
    mock_handler.assert_not_called()
    # User should receive access denied notice
    mock_msg.answer.assert_called_once()
    assert "Access Denied" in mock_msg.answer.call_args[0][0]
