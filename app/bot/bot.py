from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from app.bot.handlers import (
    chat_router,
    documents_router,
    gmail_router,
    help_router,
    jobs_router,
    memory_router,
    reminders_router,
    search_router,
    start_router,
    status_router,
)
from app.bot.middleware import SecurityMiddleware
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


_cached_bot: Optional[Bot] = None
_cached_dp: Optional[Dispatcher] = None


def create_bot() -> tuple[Bot, Dispatcher]:
    global _cached_bot, _cached_dp
    if _cached_bot is not None and _cached_dp is not None:
        return _cached_bot, _cached_dp

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Apply security & idempotency middleware
    dp.message.middleware(SecurityMiddleware())
    dp.callback_query.middleware(SecurityMiddleware())

    # Register routers in priority order
    dp.include_router(start_router)
    dp.include_router(help_router)
    dp.include_router(status_router)
    dp.include_router(search_router)
    dp.include_router(memory_router)
    dp.include_router(gmail_router)
    dp.include_router(jobs_router)
    dp.include_router(reminders_router)
    dp.include_router(documents_router)
    dp.include_router(chat_router)  # Catch-all text router

    _cached_bot = bot
    _cached_dp = dp
    return bot, dp
