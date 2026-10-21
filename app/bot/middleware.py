from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from app.database.repositories.audit_repo import AuditRepository
from app.database.repositories.user_repo import UserRepository
from app.database.session import get_db_session
from app.logging_config import get_logger
from app.security.authentication import is_user_authorized
from app.security.rate_limits import rate_limiter

logger = get_logger(__name__)


class SecurityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        user_id = user.id

        # 1. Authorization check
        if not is_user_authorized(user_id):
            logger.warning(f"Unauthorized access attempt blocked from user_id={user_id} (@{user.username})")
            if hasattr(event, "message") and event.message:
                await event.message.answer(
                    "⛔️ *Access Denied*\n\n"
                    "This is a private personal assistant. Your numeric Telegram ID is not on the allowed whitelist.",
                    parse_mode="Markdown",
                )
            elif hasattr(event, "answer"):
                # If it's a CallbackQuery, it has 'data' attribute
                if hasattr(event, "data") and getattr(event, "data", None) is not None:
                    await event.answer("⛔️ Unauthorized.", show_alert=True)
                else:
                    await event.answer(
                        "⛔️ *Access Denied*\n\n"
                        "This is a private personal assistant. Your numeric Telegram ID is not on the allowed whitelist.",
                        parse_mode="Markdown",
                    )
            return

        # 2. Rate limiting check
        if not rate_limiter.is_allowed(user_id):
            if hasattr(event, "answer") and (hasattr(event, "text") or hasattr(event, "caption")):
                await event.answer("⚠️ Too many requests. Please wait a moment before sending another message.")
            elif hasattr(event, "message") and event.message:
                await event.message.answer("⚠️ Too many requests. Please wait a moment before sending another message.")
            return

        # 3. Ensure user exists in database
        try:
            async with get_db_session() as session:
                user_repo = UserRepository(session)
                await user_repo.get_or_create(
                    user_id=user_id,
                    username=user.username,
                    full_name=user.full_name,
                )
        except Exception as e:
            logger.error(f"Error ensuring user in DB: {e}")

        # 4. Telegram update idempotency check
        if isinstance(event, Update) and event.update_id:
            try:
                async with get_db_session() as session:
                    audit_repo = AuditRepository(session)
                    if await audit_repo.is_update_processed(event.update_id):
                        logger.warning(f"Skipping duplicate Telegram update {event.update_id}")
                        return
                    await audit_repo.mark_update_processed(
                        update_id=event.update_id,
                        user_id=user_id,
                        update_type=event.event_type,
                    )
            except Exception as e:
                logger.warning(f"Idempotency check error: {e}")

        return await handler(event, data)
