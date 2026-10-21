import uuid
from typing import List, Optional
from sqlalchemy import desc, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Conversation, ConversationSummary, Message
from app.logging_config import get_logger

logger = get_logger(__name__)


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_active_conversation(self, user_id: int) -> Conversation:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        conv = result.scalars().first()
        if not conv:
            conv = Conversation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title="Default Conversation",
            )
            self.session.add(conv)
            await self.session.flush()
        return conv

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[dict] = None,
        tool_call_id: Optional[str] = None,
        token_count: int = 0,
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            token_count=token_count,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_recent_messages(self, conversation_id: str, limit: int = 12) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()  # Return in chronological order
        return messages

    async def get_latest_summary(self, conversation_id: str) -> Optional[ConversationSummary]:
        stmt = (
            select(ConversationSummary)
            .where(ConversationSummary.conversation_id == conversation_id)
            .order_by(desc(ConversationSummary.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def add_summary(self, conversation_id: str, summary_text: str, up_to_message_id: Optional[str] = None) -> ConversationSummary:
        summary = ConversationSummary(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            summary_text=summary_text,
            up_to_message_id=up_to_message_id,
        )
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def clear_summaries(self, conversation_id: str) -> int:
        stmt = delete(ConversationSummary).where(ConversationSummary.conversation_id == conversation_id)
        result = await self.session.execute(stmt)
        return result.rowcount
