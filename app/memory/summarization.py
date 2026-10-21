from typing import Optional
from app.database.repositories.conversation_repo import ConversationRepository
from app.database.session import get_db_session
from app.logging_config import get_logger
from app.providers.llm.openrouter import OpenRouterProvider

logger = get_logger(__name__)


class ConversationSummarizer:
    def __init__(self):
        self.llm = OpenRouterProvider()

    async def maybe_summarize(self, conversation_id: str, min_messages: int = 14) -> Optional[str]:
        """Summarizes older conversation turns if the message history exceeds min_messages."""
        async with get_db_session() as session:
            repo = ConversationRepository(session)
            messages = await repo.get_recent_messages(conversation_id, limit=30)
            if len(messages) < min_messages:
                return None

            latest_summary = await repo.get_latest_summary(conversation_id)
            existing_summary = latest_summary.summary_text if latest_summary else "No prior summary."

            # Construct conversation excerpt to summarize
            transcript = "\n".join(f"{m.role}: {m.content or ''}" for m in messages[:-6])

            prompt = (
                f"Existing conversation summary: {existing_summary}\n\n"
                f"New conversation transcript:\n{transcript}\n\n"
                "Provide an updated, concise factual summary of key user preferences, topics discussed, "
                "and unresolved actions in 3-5 sentences."
            )

            try:
                resp = await self.llm.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a concise conversation summarizer."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=300,
                )
                new_summary = resp.content.strip() if resp.content else ""
                if new_summary:
                    await repo.add_summary(conversation_id, new_summary)
                    logger.info(f"Updated summary for conversation {conversation_id}")
                    return new_summary
            except Exception as e:
                logger.warning(f"Failed to generate conversation summary: {e}")

        return None
