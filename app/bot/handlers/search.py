from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from app.bot.formatting import split_message
from app.tools.web_search import web_search_tool

router = Router(name="search")


@router.message(Command("search"))
async def handle_search_command(message: Message):
    args = message.text.partition(" ")[2].strip()
    if not args:
        await message.answer("ℹ️ Please provide search terms, e.g.:\n`/search latest updates on AI agents`", parse_mode="Markdown")
        return

    status_msg = await message.answer("🔎 _Searching the web..._", parse_mode="Markdown")
    res = await web_search_tool.search(query=args)

    if res.get("error"):
        await status_msg.edit_text(f"❌ Search failed:\n{res['error']}")
        return

    results = res.get("results", [])
    if not results:
        await status_msg.edit_text(f"No results found for *{args}*.", parse_mode="Markdown")
        return

    lines = [f"🔍 *Web Search Results for: {args}*\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "No Title")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        domain = r.get("source_domain", "")
        lines.append(f"*{i}. [{title}]({url})*")
        if domain:
            lines.append(f"_Source: {domain}_")
        lines.append(f"{snippet}\n")

    full_text = "\n".join(lines)
    chunks = split_message(full_text)
    await status_msg.edit_text(chunks[0], parse_mode="Markdown", disable_web_page_preview=True)
    for c in chunks[1:]:
        await message.answer(c, parse_mode="Markdown", disable_web_page_preview=True)


@router.callback_query(F.data == "action_search")
async def handle_search_callback(query: CallbackQuery):
    await query.message.answer(
        "🔎 *Web Research*\n\nSend your query using `/search <your question>` or simply ask me directly in chat!",
        parse_mode="Markdown",
    )
    await query.answer()
