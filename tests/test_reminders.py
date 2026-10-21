from datetime import datetime, timedelta, timezone
import pytest
from app.database.repositories.reminder_repo import ReminderRepository


@pytest.mark.asyncio
async def test_reminders_lifecycle(db_session):
    repo = ReminderRepository(db_session)
    user_id = 123456789

    now = datetime.now(timezone.utc)
    past_due = now - timedelta(minutes=5)
    future = now + timedelta(hours=2)

    # 1. Create a due reminder and a future reminder
    r_due = await repo.create_reminder(
        user_id=user_id,
        title="Due task",
        scheduled_at_utc=past_due,
    )
    r_future = await repo.create_reminder(
        user_id=user_id,
        title="Future task",
        scheduled_at_utc=future,
    )

    assert r_due.idempotency_key != r_future.idempotency_key

    # 2. List pending
    pending = await repo.list_user_reminders(user_id=user_id)
    assert len(pending) == 2

    # 3. Claim due reminders (atomic dispatcher check)
    claimed = await repo.claim_due_reminders(batch_size=10)
    assert len(claimed) == 1
    assert claimed[0].id == r_due.id
    assert claimed[0].attempts == 1

    # 4. Mark delivered
    await repo.mark_delivered(r_due.id)
    delivered = await repo.get_by_id(r_due.id, user_id=user_id)
    assert delivered.status == "delivered"

    # 5. Cancel future task
    cancelled = await repo.cancel_reminder(r_future.id, user_id=user_id)
    assert cancelled is True
    cancelled_r = await repo.get_by_id(r_future.id, user_id=user_id)
    assert cancelled_r.status == "cancelled"
