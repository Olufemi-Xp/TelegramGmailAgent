import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Reminder, utc_now
from app.logging_config import get_logger

logger = get_logger(__name__)


class ReminderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_reminder(
        self,
        user_id: int,
        title: str,
        scheduled_at_utc: datetime,
        description: Optional[str] = None,
        recurrence_rule: Optional[str] = None,
        tz_name: str = "Africa/Lagos",
    ) -> Reminder:
        idempotency_key = f"{user_id}_{int(scheduled_at_utc.timestamp())}_{uuid.uuid4().hex[:8]}"
        reminder = Reminder(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title.strip(),
            description=description,
            scheduled_at_utc=scheduled_at_utc,
            recurrence_rule=recurrence_rule,
            timezone=tz_name,
            status="pending",
            attempts=0,
            max_attempts=3,
            idempotency_key=idempotency_key,
            created_at=utc_now(),
        )
        self.session.add(reminder)
        await self.session.flush()
        logger.info(f"Created reminder id={reminder.id} for user {user_id} scheduled at {scheduled_at_utc} UTC")
        return reminder

    async def list_user_reminders(
        self,
        user_id: int,
        include_completed: bool = False,
        limit: int = 25,
    ) -> List[Reminder]:
        stmt = select(Reminder).where(Reminder.user_id == user_id)
        if not include_completed:
            stmt = stmt.where(Reminder.status.in_(["pending", "failed"]))
        stmt = stmt.order_by(Reminder.scheduled_at_utc.asc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id(self, reminder_id: str, user_id: int) -> Optional[Reminder]:
        stmt = select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def cancel_reminder(self, reminder_id: str, user_id: int) -> bool:
        stmt = (
            update(Reminder)
            .where(Reminder.id == reminder_id, Reminder.user_id == user_id, Reminder.status == "pending")
            .values(status="cancelled")
        )
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def mark_complete(self, reminder_id: str, user_id: int) -> bool:
        stmt = (
            update(Reminder)
            .where(Reminder.id == reminder_id, Reminder.user_id == user_id)
            .values(status="completed", delivered_at=utc_now())
        )
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def claim_due_reminders(self, batch_size: int = 10) -> List[Reminder]:
        """Atomically retrieves and locks pending reminders that are due for delivery."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Reminder)
            .where(
                Reminder.status == "pending",
                Reminder.scheduled_at_utc <= now,
                Reminder.attempts < Reminder.max_attempts,
            )
            .with_for_update(skip_locked=True)
            .limit(batch_size)
        )
        res = await self.session.execute(stmt)
        due = list(res.scalars().all())
        for r in due:
            r.attempts += 1
        await self.session.flush()
        return due

    async def mark_delivered(self, reminder_id: str):
        stmt = (
            update(Reminder)
            .where(Reminder.id == reminder_id)
            .values(status="delivered", delivered_at=utc_now())
        )
        await self.session.execute(stmt)

    async def mark_delivery_failed(self, reminder_id: str, error_msg: str):
        stmt = (
            update(Reminder)
            .where(Reminder.id == reminder_id)
            .values(
                status="failed",
                last_error=error_msg,
            )
        )
        await self.session.execute(stmt)
