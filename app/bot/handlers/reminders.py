from datetime import datetime, timezone
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from app.database.repositories.reminder_repo import ReminderRepository
from app.database.session import get_db_session

router = Router(name="reminders")


@router.message(Command("remind"))
async def handle_remind_command(message: Message):
    args = message.text.partition(" ")[2].strip()
    if not args:
        await message.answer(
            "ℹ️ *Usage:* `/remind <ISO_TIME> | <TASK_TITLE>`\n\n"
            "Example:\n`/remind 2026-10-22T09:00:00Z | Review project architecture`\n\n"
            "Or ask naturally in chat: _\"Remind me at 9am tomorrow to check emails\"_",
            parse_mode="Markdown",
        )
        return

    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await message.answer("⚠️ Please separate time and task with `|`, e.g.:\n`/remind 2026-10-22T09:00:00Z | Call doctor`", parse_mode="Markdown")
        return

    time_str, title = parts[0], parts[1]
    try:
        clean_iso = time_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        await message.answer("❌ Invalid date/time format. Please use ISO 8601 (e.g. `2026-10-22T09:00:00Z`).", parse_mode="Markdown")
        return

    async with get_db_session() as session:
        repo = ReminderRepository(session)
        rem = await repo.create_reminder(
            user_id=message.from_user.id,
            title=title,
            scheduled_at_utc=dt,
        )

    await message.answer(
        f"⏰ *Reminder Scheduled*\n\n"
        f"• *Task:* {rem.title}\n"
        f"• *Time:* `{rem.scheduled_at_utc.strftime('%Y-%m-%d %H:%M UTC')}`\n"
        f"• *ID:* `{rem.id}`",
        parse_mode="Markdown",
    )


@router.message(Command("tasks"))
async def handle_tasks_command(message: Message):
    async with get_db_session() as session:
        repo = ReminderRepository(session)
        reminders = await repo.list_user_reminders(user_id=message.from_user.id)

    if not reminders:
        await message.answer("⏰ You have no pending reminders.", parse_mode="Markdown")
        return

    lines = ["⏰ *Your Pending Reminders & Tasks:*\n"]
    for r in reminders:
        time_str = r.scheduled_at_utc.strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"• *{r.title}*")
        lines.append(f"  _Scheduled: {time_str} | Status: `{r.status}`_")
        lines.append(f"  _ID: `{r.id}`_\n")

    lines.append("💡 _To cancel a reminder, use `/cancel <id>`_")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("cancel"))
async def handle_cancel_command(message: Message):
    rem_id = message.text.partition(" ")[2].strip()
    if not rem_id:
        await message.answer("ℹ️ Please provide the reminder ID to cancel, e.g.:\n`/cancel <reminder-id>`", parse_mode="Markdown")
        return

    async with get_db_session() as session:
        repo = ReminderRepository(session)
        cancelled = await repo.cancel_reminder(reminder_id=rem_id, user_id=message.from_user.id)

    if cancelled:
        await message.answer(f"✅ Reminder `{rem_id}` has been cancelled.", parse_mode="Markdown")
    else:
        await message.answer(f"❌ Reminder `{rem_id}` not found or already completed/cancelled.", parse_mode="Markdown")


@router.callback_query(F.data == "action_tasks")
async def handle_tasks_callback(query: CallbackQuery):
    async with get_db_session() as session:
        repo = ReminderRepository(session)
        reminders = await repo.list_user_reminders(user_id=query.from_user.id)

    if not reminders:
        await query.message.answer("⏰ You have no pending tasks or reminders.", parse_mode="Markdown")
    else:
        lines = ["⏰ *Pending Tasks:*\n"]
        for r in reminders:
            lines.append(f"• *{r.title}* ({r.scheduled_at_utc.strftime('%Y-%m-%d %H:%M UTC')})\n  _ID: `{r.id}`_")
        await query.message.answer("\n".join(lines), parse_mode="Markdown")
    await query.answer()
