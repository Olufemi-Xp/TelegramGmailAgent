import asyncio
from datetime import datetime, timezone
from typing import Optional
from aiogram import Bot
from app.database.repositories.reminder_repo import ReminderRepository
from app.database.session import get_db_session
from app.logging_config import get_logger

logger = get_logger(__name__)


async def process_due_reminders(bot: Optional[Bot]) -> int:
    """Finds due reminders, claims them atomically, and sends Telegram notifications."""
    if not bot:
        logger.debug("Scheduler: Bot instance not supplied, skipping dispatch.")
        return 0

    delivered_count = 0
    async with get_db_session() as session:
        repo = ReminderRepository(session)
        due_reminders = await repo.claim_due_reminders(batch_size=10)

        for rem in due_reminders:
            try:
                # Deliver to user on Telegram
                msg_text = (
                    f"⏰ *Reminder*\n\n"
                    f"*{rem.title}*\n"
                )
                if rem.description:
                    msg_text += f"{rem.description}\n"
                msg_text += f"\n_Scheduled for: {rem.scheduled_at_utc.strftime('%Y-%m-%d %H:%M UTC')}_"

                await bot.send_message(
                    chat_id=rem.user_id,
                    text=msg_text,
                    parse_mode="Markdown",
                )
                await repo.mark_delivered(rem.id)
                delivered_count += 1
                logger.info(f"Delivered reminder id={rem.id} to user={rem.user_id}")
            except Exception as e:
                err_str = str(e)
                logger.error(f"Failed to deliver reminder id={rem.id}: {err_str}")
                await repo.mark_delivery_failed(rem.id, error_msg=err_str)

    return delivered_count
