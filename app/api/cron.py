from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from app.config import settings
from app.logging_config import get_logger
from app.scheduler.service import scheduler_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.get("/reminders")
async def trigger_reminders(authorization: Optional[str] = Header(None)):
    """Triggered periodically by Vercel Cron."""
    if settings.CRON_SECRET:
        expected = f"Bearer {settings.CRON_SECRET}"
        if authorization != expected:
            logger.warning("Rejected cron invocation: Invalid or missing authorization header.")
            raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        await scheduler_service.process_now()
        return {"status": "ok", "message": "Processed due reminders successfully."}
    except Exception as e:
        logger.error(f"Error executing serverless reminder cron: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@router.get("/inbox")
async def trigger_inbox_check(authorization: Optional[str] = Header(None)):
    """Triggered periodically (e.g., daily via Vercel Cron, or every 10m via external web cron) to check inbox."""
    if settings.CRON_SECRET:
        expected = f"Bearer {settings.CRON_SECRET}"
        if authorization != expected:
            logger.warning("Rejected cron invocation: Invalid or missing authorization header.")
            raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        stats = await scheduler_service.process_inbox_now()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        logger.error(f"Error executing serverless inbox cron: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
