from app.bot.handlers.chat import router as chat_router
from app.bot.handlers.documents import router as documents_router
from app.bot.handlers.gmail import router as gmail_router
from app.bot.handlers.help import router as help_router
from app.bot.handlers.jobs import router as jobs_router
from app.bot.handlers.memory import router as memory_router
from app.bot.handlers.reminders import router as reminders_router
from app.bot.handlers.search import router as search_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.status import router as status_router

__all__ = [
    "start_router",
    "help_router",
    "status_router",
    "search_router",
    "memory_router",
    "gmail_router",
    "jobs_router",
    "reminders_router",
    "documents_router",
    "chat_router",
]
