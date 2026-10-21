import os
from aiogram import Bot, Router
from aiogram.types import FSInputFile, Message
from app.agent.orchestrator import agent_orchestrator
from app.bot.formatting import split_message
from app.logging_config import get_logger

logger = get_logger(__name__)
router = Router(name="chat")


@router.message()
async def handle_user_chat(message: Message, bot: Bot):
    text = (message.text or "").strip()
    if not text:
        return

    # Show typing action
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response_text, file_paths = await agent_orchestrator.process_user_message(
            user_id=message.from_user.id,
            user_text=text,
        )

        # 1. Send text response chunks
        chunks = split_message(response_text)
        for chunk in chunks:
            try:
                await message.answer(chunk, parse_mode="Markdown")
            except Exception:
                # If markdown parsing fails due to unescaped special characters, fallback to plaintext
                await message.answer(chunk)

        # 2. Deliver any generated downloadable files
        for fp in file_paths:
            if os.path.exists(fp):
                file_input = FSInputFile(fp)
                await message.answer_document(
                    document=file_input,
                    caption=f"📎 Generated File: `{os.path.basename(fp)}`",
                    parse_mode="Markdown",
                )

    except Exception as e:
        logger.error(f"Error handling message from user {message.from_user.id}: {e}", exc_info=True)
        await message.answer(
            "⚠️ An unexpected error occurred while processing your request. Please try again shortly.",
        )
