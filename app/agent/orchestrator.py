import json
from typing import Any, Dict, List, Optional, Tuple
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tool_registry import tool_registry
from app.config import settings
from app.database.repositories.conversation_repo import ConversationRepository
from app.database.session import get_db_session
from app.logging_config import get_logger
from app.memory.retrieval import MemoryRetriever
from app.memory.summarization import ConversationSummarizer
from app.providers.llm.openrouter import OpenRouterProvider

logger = get_logger(__name__)


class AgentOrchestrator:
    def __init__(self):
        self.llm = OpenRouterProvider()
        self.summarizer = ConversationSummarizer()

    async def process_user_message(
        self,
        user_id: int,
        user_text: str,
        additional_context: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """Executes the agent reasoning loop for an authorized user input.
        Returns: (final_response_text, list_of_generated_file_paths)
        """
        generated_files: List[str] = []

        async with get_db_session() as session:
            conv_repo = ConversationRepository(session)
            conv = await conv_repo.get_or_create_active_conversation(user_id)
            conv_id = conv.id

            # 1. Fetch recent conversation messages
            recent_db_messages = await conv_repo.get_recent_messages(conv_id, limit=10)
            
            # 2. Fetch rolling summary
            latest_summary = await conv_repo.get_latest_summary(conv_id)

            # 3. Retrieve relevant personal memory facts and document excerpts
            mem_data = await MemoryRetriever.get_relevant_context(user_id=user_id, query=user_text)

        # 4. Build prompt context
        context_parts = []
        if latest_summary:
            context_parts.append(f"Conversation Summary So Far:\n{latest_summary.summary_text}")

        facts = mem_data.get("personal_facts", [])
        if facts:
            fact_lines = [f"- [{f['category']}] {f['content']}" for f in facts]
            context_parts.append("Known Facts & Preferences About User:\n" + "\n".join(fact_lines))

        doc_chunks = mem_data.get("document_excerpts", [])
        if doc_chunks:
            chunk_lines = [f"- From {c['document']}: {c['content']}" for c in doc_chunks]
            context_parts.append("Relevant Uploaded Document Excerpts:\n" + "\n".join(chunk_lines))

        if additional_context:
            context_parts.append(f"Direct Context:\n{additional_context}")

        system_instruction = SYSTEM_PROMPT
        if context_parts:
            system_instruction += "\n\n=== RELEVANT CONTEXT ===\n" + "\n\n".join(context_parts)

        # Build message history for LLM
        llm_messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_instruction}
        ]

        for m in recent_db_messages:
            if m.role in ("user", "assistant"):
                llm_messages.append({"role": m.role, "content": m.content or ""})

        # Append current user prompt
        llm_messages.append({"role": "user", "content": user_text})

        # 5. Agent Tool Execution Loop
        tools_schema = tool_registry.get_openai_tools()
        iteration = 0
        final_answer = ""

        while iteration < settings.MAX_TOOL_ITERATIONS:
            iteration += 1
            logger.debug(f"Agent reasoning iteration {iteration}/{settings.MAX_TOOL_ITERATIONS} for user={user_id}")

            response = await self.llm.chat_completion(
                messages=llm_messages,
                tools=tools_schema if iteration < settings.MAX_TOOL_ITERATIONS else None,
            )

            # If model produced tool calls, execute them
            if response.tool_calls:
                # Add assistant message with tool calls to history
                llm_messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                })

                for tc in response.tool_calls:
                    logger.info(f"Executing tool '{tc.name}' with args {tc.arguments}")
                    tool_res = await tool_registry.execute_tool(
                        name=tc.name,
                        arguments=tc.arguments,
                        user_id=user_id,
                    )

                    # If file was generated, record path for Telegram delivery
                    if tc.name == "generate_file" and "file_path" in tool_res:
                        generated_files.append(tool_res["file_path"])

                    # Append tool result back to model context
                    llm_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": json.dumps(tool_res),
                    })

                # Loop continues to let model synthesize answer based on tool outputs
                continue

            # If no tool calls, model gave final answer
            final_answer = response.content or "Task completed."
            break

        if not final_answer:
            final_answer = "I executed the requested operations."

        # 6. Persist conversation in database
        async with get_db_session() as session:
            conv_repo = ConversationRepository(session)
            await conv_repo.add_message(conversation_id=conv_id, role="user", content=user_text)
            await conv_repo.add_message(conversation_id=conv_id, role="assistant", content=final_answer)

        # 7. Check if rolling summary is needed in background
        try:
            await self.summarizer.maybe_summarize(conv_id)
        except Exception as e:
            logger.warning(f"Background summarization failed: {e}")

        return final_answer, generated_files


agent_orchestrator = AgentOrchestrator()
