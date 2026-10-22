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


async def process_inbox_check(bot: Optional[Bot]) -> dict:
    """Checks Gmail inbox for new unread emails across authorized users and sends Telegram notifications."""
    from app.config import settings
    from app.services.gmail_service import gmail_service

    stats = {"emails_processed": 0, "reminders_delivered": 0}

    # 1. Process due reminders
    stats["reminders_delivered"] = await process_due_reminders(bot)

    if not bot or not gmail_service.is_configured():
        return stats

    # 2. Check unread emails for authorized users
    for user_id in settings.allowed_user_ids:
        try:
            new_emails = await gmail_service.get_unprocessed_emails(user_id=user_id, max_results=5)
            if not new_emails:
                continue

            for email in new_emails:
                from_addr = email.get("from", "Unknown")
                subject = email.get("subject", "(No Subject)")
                snippet = email.get("snippet", "")
                
                # Sanitize markdown formatting characters
                safe_from = from_addr.replace("*", "").replace("_", "")
                safe_subject = subject.replace("*", "").replace("_", "")
                safe_snippet = snippet.replace("*", "").replace("_", "")[:250]

                notify_text = (
                    f"📩 *New Email in Inbox*\n\n"
                    f"*From:* {safe_from}\n"
                    f"*Subject:* {safe_subject}\n\n"
                    f"_{safe_snippet}..._\n\n"
                    f"💡 Reply with `/draft {safe_from} | Re: {safe_subject} | <your response>` to create a draft."
                )
                try:
                    await bot.send_message(chat_id=user_id, text=notify_text, parse_mode="Markdown")
                except Exception as e:
                    logger.warning(f"Failed to send email alert to Telegram user {user_id}: {e}")

            await gmail_service.mark_emails_processed(user_id=user_id, messages=new_emails)
            stats["emails_processed"] += len(new_emails)
            logger.info(f"Processed and notified {len(new_emails)} new emails for user {user_id}")
        except Exception as e:
            logger.debug(f"Inbox check skipped or error for user {user_id}: {e}")

    return stats
