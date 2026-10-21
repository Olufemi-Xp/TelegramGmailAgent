from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from app.bot.formatting import split_message
from app.database.repositories.oauth_repo import OAuthRepository
from app.database.session import get_db_session
from app.services.gmail_service import gmail_service

router = Router(name="gmail")


@router.message(Command("gmail"))
async def handle_gmail_command(message: Message):
    user_id = message.from_user.id

    if not gmail_service.is_configured():
        await message.answer(
            "⚪️ *Gmail Integration is Not Configured*\n\n"
            "To enable Gmail reading and drafting, set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your environment.",
            parse_mode="Markdown",
        )
        return

    # Check if user has connected their Google account
    is_connected = False
    async with get_db_session() as session:
        repo = OAuthRepository(session)
        creds = await repo.get_credentials(user_id=user_id)
        if creds and creds.get("access_token"):
            is_connected = True

    if not is_connected:
        auth_url = gmail_service.generate_auth_url(user_id=user_id)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔗 Connect Google Account", url=auth_url)]]
        )
        await message.answer(
            "✉️ *Gmail Account Setup*\n\n"
            "Your Google account is not connected yet. Click the button below to authorize read-only access and reply drafting.\n\n"
            "🔒 *Privacy Guarantee:*\n"
            "• Scopes are strictly restricted to reading and drafting.\n"
            "• Sending emails is disabled in code.\n"
            "• Tokens are encrypted at rest with AES-Fernet.",
            parse_mode="Markdown",
            reply_markup=kb,
        )
        return

    status_msg = await message.answer("📬 _Checking recent emails..._", parse_mode="Markdown")
    try:
        messages = await gmail_service.search_messages(user_id=user_id, query="is:unread", max_results=5)
        if not messages:
            await status_msg.edit_text("📭 Your inbox has no unread messages right now.")
            return

        lines = [f"📬 *Recent Unread Emails ({len(messages)}):*\n"]
        for i, m in enumerate(messages, 1):
            sender = m.get("from", "Unknown")
            subject = m.get("subject", "No Subject")
            date = m.get("date", "")
            snippet = m.get("snippet", "")
            lines.append(f"*{i}. From:* `{sender}`")
            lines.append(f"• *Subject:* {subject}")
            lines.append(f"• *Date:* {date}")
            lines.append(f"• *Preview:* _{snippet}_\n")

        lines.append("💡 _To draft a reply, type: `/draft <to> <subject> <body>` or ask in chat!_")
        full_text = "\n".join(lines)
        chunks = split_message(full_text)
        await status_msg.edit_text(chunks[0], parse_mode="Markdown")
        for c in chunks[1:]:
            await message.answer(c, parse_mode="Markdown")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error fetching emails: {str(e)}")


@router.message(Command("draft"))
async def handle_draft_command(message: Message):
    args = message.text.partition(" ")[2].strip()
    if not args:
        await message.answer(
            "ℹ️ *Draft Email Usage:*\n"
            "You can ask naturally: _\"Draft an email to recruiter@example.com accepting the interview\"_\n\n"
            "Or use: `/draft <recipient> | <subject> | <body>`",
            parse_mode="Markdown",
        )
        return

    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 3:
        await message.answer("⚠️ Please provide all 3 fields separated by `|`:\n`/draft user@example.com | Hello | Thanks for the update`", parse_mode="Markdown")
        return

    to_addr, subject, body = parts[0], parts[1], parts[2]
    status_msg = await message.answer("📝 _Preparing draft in Gmail..._", parse_mode="Markdown")

    try:
        res = await gmail_service.create_draft(user_id=message.from_user.id, to=to_addr, subject=subject, body=body)
        await status_msg.edit_text(
            f"✅ *Draft Created in Gmail*\n\n"
            f"• *To:* `{to_addr}`\n"
            f"• *Subject:* {subject}\n"
            f"• *Draft ID:* `{res.get('draft_id')}`\n\n"
            f"🔒 _Note: As a safety precaution, emails can only be sent manually by you from your Gmail client._",
            parse_mode="Markdown",
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to create draft: {str(e)}")


@router.callback_query(F.data == "action_gmail")
async def handle_gmail_callback(query: CallbackQuery):
    await query.message.answer(
        "✉️ *Gmail Integration*\n\nUse `/gmail` to view recent emails or `/draft` to compose a draft.",
        parse_mode="Markdown",
    )
    await query.answer()
