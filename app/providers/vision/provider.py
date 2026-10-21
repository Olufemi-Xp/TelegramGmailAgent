import base64
from typing import Optional
import httpx
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class VisionService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.VISION_MODEL
        self.base_url = settings.OPENROUTER_BASE_URL.rstrip("/")

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        prompt: str = "Please describe and analyze this image in detail.",
    ) -> str:
        """Sends an image to the configured vision-capable model on OpenRouter."""
        if not self.api_key:
            raise RuntimeError("Vision model processing requires OPENROUTER_API_KEY.")

        if not image_bytes:
            raise ValueError("Image buffer is empty.")

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_img}"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                    ],
                }
            ],
            "max_tokens": 1024,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title": settings.OPENROUTER_APP_NAME,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Vision model error ({resp.status_code}): {resp.text}")
            
            data = resp.json()
            choice = data.get("choices", [{}])[0]
            answer = choice.get("message", {}).get("content", "").strip()
            return answer


vision_service = VisionService()
