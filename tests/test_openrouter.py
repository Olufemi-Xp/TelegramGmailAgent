import json
import pytest
from unittest.mock import AsyncMock, patch
from app.providers.llm.openrouter import OpenRouterProvider, strip_thinking_tags


def test_strip_thinking_tags():
    raw_response = "<think>The user wants to find jobs. Let me think about parameters.</think>Here are the jobs found."
    cleaned = strip_thinking_tags(raw_response)
    assert cleaned == "Here are the jobs found."
    assert "<think>" not in cleaned

    assert strip_thinking_tags("Ordinary answer without tags.") == "Ordinary answer without tags."
    assert strip_thinking_tags(None) is None


@pytest.mark.asyncio
async def test_openrouter_mocked_completion():
    provider = OpenRouterProvider(api_key="fake-key")

    mock_response_data = {
        "model": "openai/gpt-oss-120b",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "<think>Processing request</think>The capital of France is Paris.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 8,
            "total_tokens": 23,
        },
    }

    with patch.object(provider, "_execute_request", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_response_data

        resp = await provider.chat_completion(
            messages=[{"role": "user", "content": "What is the capital of France?"}]
        )

        assert resp.content == "The capital of France is Paris."
        assert resp.model == "openai/gpt-oss-120b"
        assert resp.total_tokens == 23
        assert resp.tool_calls == []


@pytest.mark.asyncio
async def test_openrouter_tool_call_parsing():
    provider = OpenRouterProvider(api_key="fake-key")

    mock_tool_call_data = {
        "model": "openai/gpt-oss-120b",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "web_search",
                                "arguments": json.dumps({"query": "latest AI news", "max_results": 3}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10},
    }

    with patch.object(provider, "_execute_request", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_tool_call_data

        resp = await provider.chat_completion(
            messages=[{"role": "user", "content": "Search for latest AI news"}]
        )

        assert len(resp.tool_calls) == 1
        tc = resp.tool_calls[0]
        assert tc.id == "call_123"
        assert tc.name == "web_search"
        assert tc.arguments["query"] == "latest AI news"
        assert tc.arguments["max_results"] == 3
