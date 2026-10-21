import os
from typing import Optional
import httpx
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class TranscriptionService:
    def __init__(self):
        pass

    def _resolve_provider_and_key(self):
        configured = settings.TRANSCRIPTION_PROVIDER.lower()
        if configured == "none":
            return "none", None, None, None

        # Check Groq first if key provided
        groq_key = settings.GROQ_API_KEY or (settings.TRANSCRIPTION_API_KEY if settings.TRANSCRIPTION_API_KEY.startswith("gsk_") else None)
        if configured == "groq" or (configured == "auto" and groq_key):
            if not groq_key:
                raise RuntimeError("Groq transcription selected but neither GROQ_API_KEY nor TRANSCRIPTION_API_KEY is set.")
            return "groq", "https://api.groq.com/openai/v1/audio/transcriptions", "whisper-large-v3-turbo", groq_key

        # Check OpenRouter
        openrouter_key = settings.TRANSCRIPTION_API_KEY if settings.TRANSCRIPTION_API_KEY.startswith("sk-or-") else settings.OPENROUTER_API_KEY
        if configured == "openrouter" or (configured == "auto" and openrouter_key):
            return "openrouter", "https://openrouter.ai/api/v1/audio/transcriptions", "openai/whisper-large-v3", openrouter_key

        # Check OpenAI
        openai_key = settings.TRANSCRIPTION_API_KEY
        if configured == "openai" or (configured == "auto" and openai_key):
            return "openai", "https://api.openai.com/v1/audio/transcriptions", "whisper-1", openai_key

        # If explicit provider requested without key
        if configured in ("openrouter", "groq", "openai"):
            raise RuntimeError(f"Transcription provider '{configured}' configured but no valid API key was found.")

        raise RuntimeError("No voice transcription provider configured. Set GROQ_API_KEY (free at console.groq.com) or OPENROUTER_API_KEY in .env.")

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg") -> str:
        """Transcribes audio file bytes into text using configured transcription provider."""
        if not audio_bytes:
            raise ValueError("Audio buffer is empty.")

        provider, endpoint, model_name, api_key = self._resolve_provider_and_key()
        if provider == "none":
            raise RuntimeError("Voice transcription is disabled (TRANSCRIPTION_PROVIDER='none').")

        files = {"file": (filename, audio_bytes, "audio/ogg")}
        data = {"model": model_name, "language": "en"}
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(endpoint, headers=headers, files=files, data=data)
            if resp.status_code == 402:
                err_msg = resp.text
                if "requires at least $0.50 in balance" in err_msg or "credits" in err_msg:
                    raise RuntimeError(
                        "OpenRouter requires at least $0.50 in credit balance for Whisper audio transcription. "
                        "Tip: You can get 100% free Whisper transcription by getting a free API key at https://console.groq.com and adding GROQ_API_KEY=gsk_... to your .env file."
                    )
                raise RuntimeError(f"Transcription billing error (402): {err_msg}")

            if resp.status_code == 401:
                raise RuntimeError(
                    f"Transcription unauthorized (401) on {provider}. Check that your API key is active and valid."
                )

            if resp.status_code != 200:
                logger.error(f"Transcription error ({resp.status_code}): {resp.text}")
                raise RuntimeError(f"Transcription failed ({resp.status_code}): {resp.text}")

            result = resp.json()
            text = result.get("text", "").strip()
            if not text:
                raise RuntimeError("Audio transcription returned empty text.")
            return text


transcription_service = TranscriptionService()
