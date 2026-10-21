import json
import pytest
from unittest.mock import AsyncMock, patch
from app.agent.orchestrator import AgentOrchestrator
from app.database.repositories.memory_repo import MemoryRepository
from app.providers.llm.base import LLMResponse, ToolCall
from app.services.file_service import file_generator


@pytest.mark.asyncio
async def test_e2e_general_conversation(db_session):
    orchestrator = AgentOrchestrator()
    user_id = 123456789

    mock_llm_resp = LLMResponse(
        content="Antigravity is an AI developer platform.",
        model="openai/gpt-oss-120b",
        prompt_tokens=20,
        completion_tokens=10,
        total_tokens=30,
    )

    with patch.object(orchestrator.llm, "chat_completion", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_llm_resp

        answer, files = await orchestrator.process_user_message(
            user_id=user_id,
            user_text="What is Antigravity?",
        )

        assert "Antigravity is an AI developer platform." in answer
        assert len(files) == 0


@pytest.mark.asyncio
async def test_e2e_research_flow_with_citations(db_session):
    orchestrator = AgentOrchestrator()
    user_id = 123456789

    # Turn 1: Model requests web_search tool
    tool_call_resp = LLMResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="call_search_1",
                name="web_search",
                arguments={"query": "quantum computing breakthroughs 2026", "max_results": 2},
            )
        ],
        model="openai/gpt-oss-120b",
    )

    # Turn 2: Model synthesizes answer based on search tool result
    final_synthesis_resp = LLMResponse(
        content="Recent breakthroughs in 2026 include topological qubits [Source: nature.com].",
        model="openai/gpt-oss-120b",
    )

    with patch.object(orchestrator.llm, "chat_completion", new_callable=AsyncMock) as mock_chat:
        mock_chat.side_effect = [tool_call_resp, final_synthesis_resp]

        answer, files = await orchestrator.process_user_message(
            user_id=user_id,
            user_text="What are the latest 2026 breakthroughs in quantum computing?",
        )

        assert "topological qubits" in answer
        assert mock_chat.call_count == 2


@pytest.mark.asyncio
async def test_e2e_memory_retention_flow(db_session):
    orchestrator = AgentOrchestrator()
    user_id = 123456789

    # 1. Store a personal fact in memory
    repo = MemoryRepository(db_session)
    await repo.add_memory(
        user_id=user_id,
        content="User is a Principal Engineer specialized in Rust and Distributed Systems.",
        category="career",
    )
    await db_session.commit()

    # 2. When asking a question, orchestrator automatically includes this fact in context
    captured_messages = []

    async def mock_chat_completion(messages, **kwargs):
        captured_messages.extend(messages)
        return LLMResponse(
            content="Based on your background in Rust and Distributed Systems, I recommend Axum.",
            model="openai/gpt-oss-120b",
        )

    with patch.object(orchestrator.llm, "chat_completion", side_effect=mock_chat_completion):
        answer, _ = await orchestrator.process_user_message(
            user_id=user_id,
            user_text="What web framework fits my background best?",
        )

        # Verify personal memory was injected into system prompt context
        system_content = captured_messages[0]["content"]
        assert "Principal Engineer specialized in Rust" in system_content
        assert "Axum" in answer


@pytest.mark.asyncio
async def test_e2e_file_generation_flow(db_session):
    orchestrator = AgentOrchestrator()
    user_id = 123456789

    # Model requests generate_file tool
    tool_call_resp = LLMResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="call_gen_1",
                name="generate_file",
                arguments={
                    "file_type": "txt",
                    "filename": "summary_notes.txt",
                    "content": "These are the synthesized meeting notes.",
                },
            )
        ],
        model="openai/gpt-oss-120b",
    )

    final_resp = LLMResponse(
        content="I have generated your meeting notes file.",
        model="openai/gpt-oss-120b",
    )

    with patch.object(orchestrator.llm, "chat_completion", side_effect=[tool_call_resp, final_resp]):
        answer, files = await orchestrator.process_user_message(
            user_id=user_id,
            user_text="Create a notes file for my meeting.",
        )

        assert "generated your meeting notes file" in answer
        assert len(files) == 1
        assert files[0].endswith("summary_notes.txt")
