import os
from typing import Optional
import httpx
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class TranscriptionService:
    def __init__(self):
        self.provider = settings.TRANSCRIPTION_PROVIDER.lower()
        self.api_key = settings.TRANSCRIPTION_API_KEY or settings.OPENROUTER_API_KEY

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg") -> str:
        """Transcribes audio file bytes into text using configured transcription provider."""
        if not audio_bytes:
            raise ValueError("Audio buffer is empty.")

        if self.provider == "none":
            raise RuntimeError("Voice transcription is not enabled. Please configure TRANSCRIPTION_PROVIDER.")

        # Default: Groq or OpenAI whisper endpoint
        if self.provider in ("groq", "openai", "openrouter"):
            if not self.api_key:
                raise RuntimeError(f"Transcription provider '{self.provider}' requires an API key.")

            endpoint = (
                "https://api.groq.com/openai/v1/audio/transcriptions"
                if self.provider == "groq"
                else "https://api.openai.com/v1/audio/transcriptions"
            )
            model_name = "whisper-large-v3" if self.provider == "groq" else "whisper-1"

            files = {"file": (filename, audio_bytes, "audio/ogg")}
            data = {"model": model_name, "language": "en"}
            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(endpoint, headers=headers, files=files, data=data)
                if resp.status_code != 200:
                    logger.error(f"Transcription error ({resp.status_code}): {resp.text}")
                    raise RuntimeError(f"Transcription failed ({resp.status_code}): {resp.text}")
                
                result = resp.json()
                text = result.get("text", "").strip()
                if not text:
                    raise RuntimeError("Audio transcription returned empty text.")
                return text

        raise NotImplementedError(f"Unsupported transcription provider: {self.provider}")


transcription_service = TranscriptionService()
