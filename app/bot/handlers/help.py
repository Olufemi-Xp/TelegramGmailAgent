from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="help")


@router.message(Command("help"))
async def handle_help(message: Message):
    help_text = (
        "📖 *Assistant Command Reference*\n\n"
        "• `/start` — Welcome message and quick navigation\n"
        "• `/help` — Show this command reference\n"
        "• `/status` — System health and active integrations\n"
        "• `/ask <query>` — Ask a question or trigger research\n"
        "• `/search <query>` — Perform live web search with citations\n"
        "• `/memory` — Inspect personal memory and indexed documents\n"
        "• `/remember <fact>` — Save a specific personal fact or preference\n"
        "• `/forget <id>` — Permanently delete a stored memory fact\n"
        "• `/upload` — Instructions for uploading CVs, PDFs, and documents\n"
        "• `/jobs <query>` — Search for remote jobs or freelance gigs\n"
        "• `/gmail` — Summarize recent inbox or view connection status\n"
        "• `/draft <details>` — Prepare a draft email reply\n"
        "• `/remind <time> <task>` — Schedule a reminder (e.g. `/remind 2026-10-22T09:00:00Z Call accountant`)\n"
        "• `/tasks` — View your pending reminders and tasks\n"
        "• `/cancel <id>` — Cancel an active reminder\n"
        "• `/settings` — View your configuration preferences\n\n"
        "💬 *Natural Language:* You can also type freely! For example:\n"
        "_\"Find remote AI engineer jobs\"_\n"
        "_\"Summarize my unread emails\"_\n"
        "_\"Remind me tomorrow at 9am to check server logs\"_\n"
        "_\"Generate a CSV spreadsheet of recent job opportunities\"_"
    )
    await message.answer(help_text, parse_mode="Markdown")
