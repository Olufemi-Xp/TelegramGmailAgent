from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from app.bot.keyboards import get_start_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message):
    welcome_text = (
        f"👋 *Welcome, {message.from_user.first_name}!*\n\n"
        "I am your private, production-ready *Personal AI Assistant*.\n\n"
        "🔒 *Security & Privacy:*\n"
        "• Your messages and memories are private and encrypted.\n"
        "• Actions are sandboxed with zero unrestricted system access.\n"
        "• Email drafting is supported; sending emails is strictly disabled.\n\n"
        "⚡️ *Core Capabilities:*\n"
        "• 🔍 *Deep Web Research* (Perplexity, Tavily, Google Search)\n"
        "• 🧠 *Persistent Memory* (Personal facts & semantic document search)\n"
        "• 💼 *Job & Gig Discovery* (Automatic deduplication)\n"
        "• ✉️ *Gmail Integration* (Search, summarize, draft)\n"
        "• ⏰ *Durable Reminders* (PostgreSQL-backed schedules)\n"
        "• 📄 *File Processing & Reports* (PDF, DOCX, CSV, TXT)\n"
        "• 🎙 *Voice & Vision* (Transcribe voice notes & analyze photos)\n\n"
        "Type any question directly, or tap below to explore:"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_start_keyboard())
