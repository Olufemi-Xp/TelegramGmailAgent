import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import (
    AuditEvent,
    PendingApproval,
    TelegramUpdate,
    ToolExecution,
    utc_now,
)
from app.logging_config import get_logger

logger = get_logger(__name__)


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_update_processed(self, update_id: int) -> bool:
        stmt = select(TelegramUpdate.update_id).where(TelegramUpdate.update_id == update_id).limit(1)
        res = await self.session.execute(stmt)
        return res.scalars().first() is not None

    async def mark_update_processed(self, update_id: int, user_id: Optional[int] = None, update_type: Optional[str] = None):
        rec = TelegramUpdate(
            update_id=update_id,
            user_id=user_id,
            update_type=update_type,
            processed_at=utc_now(),
        )
        self.session.add(rec)
        await self.session.flush()

    async def record_tool_execution(
        self,
        tool_name: str,
        user_id: Optional[int],
        tool_args: Dict[str, Any],
        tool_result: Dict[str, Any],
        is_success: bool,
        execution_time_ms: int,
        failure_category: Optional[str] = None,
    ) -> ToolExecution:
        # Sanitize sensitive arguments before recording in database
        clean_args = {k: ("[REDACTED]" if any(s in k.lower() for s in ["key", "token", "auth", "secret"]) else v) for k, v in tool_args.items()}
        rec = ToolExecution(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tool_name=tool_name,
            tool_args=clean_args,
            tool_result=tool_result,
            is_success=is_success,
            execution_time_ms=execution_time_ms,
            failure_category=failure_category,
            created_at=utc_now(),
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def record_audit_event(self, event_type: str, user_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> AuditEvent:
        rec = AuditEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type=event_type,
            details=details or {},
            ip_address=ip_address,
            created_at=utc_now(),
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def create_pending_approval(self, user_id: int, action_type: str, action_args: Dict[str, Any], expires_at: datetime) -> PendingApproval:
        rec = PendingApproval(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action_type=action_type,
            action_args=action_args,
            status="pending",
            expires_at=expires_at,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_pending_approval(self, approval_id: str) -> Optional[PendingApproval]:
        stmt = select(PendingApproval).where(PendingApproval.id == approval_id)
        res = await self.session.execute(stmt)
        return res.scalars().first()
