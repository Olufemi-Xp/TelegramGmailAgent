import asyncio
from typing import Optional
from aiogram import Bot
from app.logging_config import get_logger
from app.scheduler.jobs import process_due_reminders

logger = get_logger(__name__)


class SchedulerService:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._bot: Optional[Bot] = None
        self._check_interval_seconds = 20

    def set_bot(self, bot: Bot):
        self._bot = bot

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Durable reminder scheduler started.")

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Durable reminder scheduler stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await process_due_reminders(self._bot)
            except Exception as e:
                logger.error(f"Error in reminder scheduler cycle: {e}")
            
            try:
                await asyncio.sleep(self._check_interval_seconds)
            except asyncio.CancelledError:
                break


scheduler_service = SchedulerService()
