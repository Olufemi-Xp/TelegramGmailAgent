from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from app.bot.keyboards import get_memory_keyboard
from app.memory.service import memory_service

router = Router(name="memory")


@router.message(Command("memory"))
async def handle_memory_command(message: Message):
    stats = await memory_service.get_memory_stats(message.from_user.id)
    total_facts = stats["total_facts"]
    breakdown = stats["category_breakdown"]
    total_docs = stats["total_documents"]

    bd_lines = [f"• `{cat}`: {count}" for cat, count in breakdown.items()] if breakdown else ["_No facts stored yet._"]

    text = (
        "🧠 *Personal Memory Overview*\n\n"
        f"• *Total Stored Facts:* {total_facts}\n"
        f"• *Uploaded Documents:* {total_docs}\n\n"
        "*Category Breakdown:*\n" + "\n".join(bd_lines) + "\n\n"
        "💡 *Memory Commands:*\n"
        "• `/remember <fact>` — Save a specific personal fact or preference\n"
        "• `/forget <id>` — Permanently remove a specific memory fact\n"
        "• `/upload` — Upload a CV or document to semantic memory"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_memory_keyboard())


@router.message(Command("remember"))
async def handle_remember_command(message: Message):
    content = message.text.partition(" ")[2].strip()
    if not content:
        await message.answer("ℹ️ Please provide the fact to remember, e.g.:\n`/remember I prefer Python and FastAPI for backend development`", parse_mode="Markdown")
        return

    result = await memory_service.save_fact(user_id=message.from_user.id, content=content)
    await message.answer(
        f"✅ *Saved to Memory*\n\n"
        f"• *ID:* `{result['id']}`\n"
        f"• *Category:* `{result['category']}`\n"
        f"• *Fact:* {result['content']}",
        parse_mode="Markdown",
    )


@router.message(Command("forget"))
async def handle_forget_command(message: Message):
    mem_id = message.text.partition(" ")[2].strip()
    if not mem_id:
        await message.answer("ℹ️ Please specify the memory ID to delete, e.g.:\n`/forget <memory-id>`", parse_mode="Markdown")
        return

    deleted = await memory_service.delete_fact(user_id=message.from_user.id, memory_id=mem_id)
    if deleted:
        await message.answer(f"🗑 Memory `{mem_id}` has been permanently deleted.", parse_mode="Markdown")
    else:
        await message.answer(f"❌ Memory `{mem_id}` not found or already deleted.", parse_mode="Markdown")


@router.callback_query(F.data == "mem_list_docs")
async def handle_list_docs_callback(query: CallbackQuery):
    docs = await memory_service.list_documents(query.from_user.id)
    if not docs:
        await query.message.answer("📄 *No documents indexed yet.*\nUse `/upload` to send a PDF or document.", parse_mode="Markdown")
    else:
        lines = ["📄 *Your Uploaded Documents:*\n"]
        for d in docs:
            lines.append(f"• *{d['filename']}* (`{d['file_type'].upper()}`, {d['size_kb']} KB, {d['chunk_count']} chunks)")
            lines.append(f"  _ID: `{d['id']}`_\n")
        await query.message.answer("\n".join(lines), parse_mode="Markdown")
    await query.answer()


@router.callback_query(F.data == "mem_clear_summary")
async def handle_clear_summary_callback(query: CallbackQuery):
    cleared = await memory_service.clear_summary(query.from_user.id)
    if cleared:
        await query.message.answer("🧹 Rolling conversation summary has been cleared.")
    else:
        await query.message.answer("ℹ️ No active conversation summary found to clear.")
    await query.answer()


@router.callback_query(F.data == "action_memory")
async def handle_memory_action_callback(query: CallbackQuery):
    stats = await memory_service.get_memory_stats(query.from_user.id)
    text = f"🧠 *Personal Memory:*\n\n• Stored facts: {stats['total_facts']}\n• Uploaded documents: {stats['total_documents']}"
    await query.message.answer(text, parse_mode="Markdown", reply_markup=get_memory_keyboard())
    await query.answer()
