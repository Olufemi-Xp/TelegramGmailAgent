from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from app.bot.bot import create_bot
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["telegram"])

_bot: Optional[Bot] = None
_dp: Optional[Dispatcher] = None


def get_bot_and_dp() -> tuple[Bot, Dispatcher]:
    global _bot, _dp
    if _bot is None or _dp is None:
        _bot, _dp = create_bot()
    return _bot, _dp


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """Handles incoming webhook updates directly from Telegram Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")

    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Rejected webhook request: Invalid secret token header.")
            raise HTTPException(status_code=403, detail="Invalid secret token")

    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    bot, dp = get_bot_and_dp()

    try:
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing Telegram webhook update: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@router.get("/set-webhook")
async def set_webhook(request: Request, url: Optional[str] = None):
    """Convenience endpoint to configure Telegram webhook with one click.
    
    Usage:
      GET https://<your-app>.vercel.app/api/telegram/set-webhook
      or pass explicit URL: ?url=https://<your-app>.vercel.app/api/telegram/webhook
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")

    target_url = url or settings.TELEGRAM_WEBHOOK_URL
    if not target_url:
        # Fallback: derive base URL directly from incoming request
        base = str(request.base_url).rstrip("/")
        if request.headers.get("x-forwarded-proto") == "https" and base.startswith("http://"):
            base = "https://" + base[7:]
        target_url = base

    if not target_url.endswith("/api/telegram/webhook"):
        target_url = target_url.rstrip("/") + "/api/telegram/webhook"

    bot, _ = get_bot_and_dp()
    secret = settings.TELEGRAM_WEBHOOK_SECRET or None

    try:
        success = await bot.set_webhook(
            url=target_url,
            secret_token=secret,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "inline_query"]
        )
        return {
            "status": "success" if success else "failed",
            "webhook_url": target_url,
            "has_secret": bool(secret),
        }
    except Exception as e:
        logger.error(f"Failed to set Telegram webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Telegram API error: {str(e)}")


@router.get("/webhook-info")
async def webhook_info():
    """Queries current Telegram webhook status from Telegram Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")

    bot, _ = get_bot_and_dp()
    try:
        info = await bot.get_webhook_info()
        return {
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "ip_address": info.ip_address,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telegram API error: {str(e)}")


@router.get("/delete-webhook")
async def delete_webhook():
    """Deletes the webhook to switch back to local polling mode."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")

    bot, _ = get_bot_and_dp()
    try:
        success = await bot.delete_webhook(drop_pending_updates=False)
        return {"status": "success" if success else "failed", "mode": "polling"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telegram API error: {str(e)}")
