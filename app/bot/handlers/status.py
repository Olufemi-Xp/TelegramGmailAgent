from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from app.config import settings
from app.database.session import check_db_health
from app.database.repositories.oauth_repo import OAuthRepository
from app.database.session import get_db_session
from app.security.rate_limits import budget_tracker

router = Router(name="status")


async def build_status_text(user_id: int) -> str:
    db_healthy = await check_db_health()
    db_str = "🟢 Connected (PostgreSQL/pgvector)" if (db_healthy and settings.is_postgres) else ("🟢 Connected (SQLite)" if db_healthy else "🔴 Disconnected")

    # Check Gmail connection for user
    gmail_connected = False
    try:
        async with get_db_session() as session:
            repo = OAuthRepository(session)
            creds = await repo.get_credentials(user_id=user_id)
            gmail_connected = bool(creds and creds.get("access_token"))
    except Exception:
        gmail_connected = False

    gmail_str = "🟢 Connected" if gmail_connected else ("🟡 Configured (Needs Auth)" if settings.has_gmail_configured else "⚪️ Disabled")

    search_status = []
    if settings.PERPLEXITY_API_KEY:
        search_status.append(f"Perplexity ({settings.PERPLEXITY_MODEL})")
    if settings.TAVILY_API_KEY:
        search_status.append("Tavily")
    if settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_ENGINE_ID:
        search_status.append("Google Search")
    search_str = ", ".join(search_status) if search_status else "None configured"

    daily_cost = budget_tracker.daily_cost
    monthly_cost = budget_tracker.monthly_cost

    return (
        "📊 *System & Integration Diagnostics*\n\n"
        f"• *Environment:* `{settings.APP_ENV}`\n"
        f"• *Timezone:* `{settings.APP_TIMEZONE}`\n"
        f"• *Database:* {db_str}\n"
        f"• *LLM Gateway:* OpenRouter (`{settings.OPENROUTER_MODEL}`)\n"
        f"• *Fallback Model:* `{settings.OPENROUTER_FALLBACK_MODEL}`\n"
        f"• *Search Providers:* {search_str}\n"
        f"• *Gmail Integration:* {gmail_str}\n"
        f"• *Embeddings:* `{settings.EMBEDDING_PROVIDER}` (`{settings.EMBEDDING_MODEL}`)\n"
        f"• *Voice Transcription:* `{settings.TRANSCRIPTION_PROVIDER}`\n"
        f"• *Vision Processing:* `{settings.VISION_MODEL}`\n"
        f"• *Daily Budget Used:* `${daily_cost:.3f}` / `${settings.DAILY_MODEL_BUDGET:.2f}`\n"
        f"• *Monthly Budget Used:* `${monthly_cost:.3f}` / `${settings.MONTHLY_MODEL_BUDGET:.2f}`\n\n"
        "🔒 _All secrets and sensitive authorization headers remain encrypted and redacted._"
    )


@router.message(Command("status"))
async def handle_status_command(message: Message):
    text = await build_status_text(message.from_user.id)
    await message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data == "action_status")
async def handle_status_callback(query: CallbackQuery):
    text = await build_status_text(query.from_user.id)
    await query.message.answer(text, parse_mode="Markdown")
    await query.answer()
