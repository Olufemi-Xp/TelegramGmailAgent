import io
import os
import uuid
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from app.agent.orchestrator import agent_orchestrator
from app.bot.formatting import split_message
from app.config import settings
from app.logging_config import get_logger
from app.memory.service import memory_service
from app.providers.transcription.provider import transcription_service
from app.providers.vision.provider import vision_service

logger = get_logger(__name__)
router = Router(name="documents")


@router.message(Command("upload"))
async def handle_upload_command(message: Message):
    await message.answer(
        "📄 *Upload Documents & CVs*\n\n"
        "Send any document directly to this chat as a file attachment.\n\n"
        "Supported formats: `.pdf`, `.docx`, `.txt`, `.csv`, `.md` (Max: 20MB).\n\n"
        "The assistant will automatically extract text, split it into chunks, generate dense vector embeddings, "
        "and index it into your private semantic memory.",
        parse_mode="Markdown",
    )


@router.message(F.document)
async def handle_document_upload(message: Message, bot: Bot):
    doc = message.document
    filename = doc.file_name or f"doc_{uuid.uuid4().hex[:6]}.bin"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in (".pdf", ".docx", ".txt", ".csv", ".md"):
        await message.answer(f"⚠️ Unsupported file type '{ext}'. Allowed: `.pdf`, `.docx`, `.txt`, `.csv`, `.md`", parse_mode="Markdown")
        return

    status_msg = await message.answer(f"📥 _Downloading and indexing '{filename}'..._", parse_mode="Markdown")

    try:
        # Save file to storage
        docs_dir = os.path.abspath(os.path.join(settings.STORAGE_DIR, "documents"))
        os.makedirs(docs_dir, exist_ok=True)
        local_path = os.path.join(docs_dir, f"{uuid.uuid4().hex[:6]}_{filename}")

        file_info = await bot.get_file(doc.file_id)
        await bot.download_file(file_info.file_path, local_path)

        res = await memory_service.index_file(
            user_id=message.from_user.id,
            file_path=local_path,
            filename=filename,
        )

        await status_msg.edit_text(
            f"✅ *Document Indexed Successfully*\n\n"
            f"• *File:* `{res['filename']}`\n"
            f"• *Document ID:* `{res['document_id']}`\n"
            f"• *Pages:* {res['page_count']}\n"
            f"• *Vector Chunks:* {res['chunk_count']}\n\n"
            "You can now ask questions about this document or reference it in job searches!",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Failed to process document {filename}: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Document indexing failed: {str(e)}")


@router.message(F.voice | F.audio)
async def handle_voice_message(message: Message, bot: Bot):
    status_msg = await message.answer("🎙 _Transcribing audio..._", parse_mode="Markdown")
    audio = message.voice or message.audio

    try:
        file_info = await bot.get_file(audio.file_id)
        audio_stream = io.BytesIO()
        await bot.download_file(file_info.file_path, audio_stream)
        audio_bytes = audio_stream.getvalue()

        # Transcribe audio
        transcript = await transcription_service.transcribe(audio_bytes, filename="voice.ogg")
        await status_msg.edit_text(f"🎙 *Transcribed:* _{transcript}_\n\n🧠 _Thinking..._", parse_mode="Markdown")

        # Process through agent loop
        answer, files = await agent_orchestrator.process_user_message(
            user_id=message.from_user.id,
            user_text=transcript,
        )

        chunks = split_message(f"🎙 *Voice Query:* {transcript}\n\n{answer}")
        for c in chunks:
            await message.answer(c, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Voice processing failed: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Voice processing failed: {str(e)}\nPlease try sending your message as text.")


@router.message(F.photo)
async def handle_photo_message(message: Message, bot: Bot):
    status_msg = await message.answer("🖼 _Analyzing image..._", parse_mode="Markdown")
    try:
        # Get highest resolution photo
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        img_stream = io.BytesIO()
        await bot.download_file(file_info.file_path, img_stream)
        img_bytes = img_stream.getvalue()

        user_prompt = message.caption or "Analyze this image in detail and describe what is visible."
        analysis = await vision_service.analyze_image(image_bytes=img_bytes, prompt=user_prompt)

        chunks = split_message(f"🖼 *Image Analysis:*\n\n{analysis}")
        await status_msg.edit_text(chunks[0], parse_mode="Markdown")
        for c in chunks[1:]:
            await message.answer(c, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Vision processing failed: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Image inspection failed: {str(e)}")
