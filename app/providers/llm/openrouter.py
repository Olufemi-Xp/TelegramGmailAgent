import asyncio
import json
import random
import re
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings
from app.logging_config import get_logger
from app.providers.llm.base import BaseLLMProvider, LLMResponse, ToolCall
from app.security.rate_limits import budget_tracker

logger = get_logger(__name__)

THINK_TAG_REGEX = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_thinking_tags(text: Optional[str]) -> Optional[str]:
    """Removes model chain-of-thought tags (e.g. <think>...</think>) from responses."""
    if not text:
        return text
    cleaned = THINK_TAG_REGEX.sub("", text).strip()
    return cleaned


class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        self.primary_model = settings.OPENROUTER_MODEL
        self.fallback_model = settings.OPENROUTER_FALLBACK_MODEL

    async def _execute_request(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title": settings.OPENROUTER_APP_NAME,
            "Content-Type": "application/json",
        }

        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=settings.REQUEST_TIMEOUT_SECONDS)
                
                # Check for rate limits or server errors
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", delay))
                    jitter = random.uniform(0.5, 1.5)
                    wait_time = min(retry_after + jitter, 15.0)
                    logger.warning(f"OpenRouter 429 Rate Limit (attempt {attempt}/{max_retries}). Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    delay *= 2
                    continue

                if 500 <= response.status_code < 600:
                    jitter = random.uniform(0.1, 0.5)
                    logger.warning(f"OpenRouter Server Error {response.status_code} (attempt {attempt}/{max_retries}). Retrying in {delay + jitter:.1f}s...")
                    await asyncio.sleep(delay + jitter)
                    delay *= 2
                    continue

                # Permanent client error (401, 403, 400)
                if response.status_code != 200:
                    err_msg = response.text
                    logger.error(f"OpenRouter API HTTP {response.status_code}: {err_msg}")
                    raise RuntimeError(f"OpenRouter error ({response.status_code}): {err_msg}")

                return response.json()

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"Network error contacting OpenRouter on attempt {attempt}: {e}")
                if attempt == max_retries:
                    raise
                await asyncio.sleep(delay + random.uniform(0.1, 0.5))
                delay *= 2

        raise RuntimeError("Exceeded maximum retries contacting OpenRouter.")

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        # Check budget limits first
        is_exceeded, reason = budget_tracker.is_budget_exceeded()
        if is_exceeded:
            raise RuntimeError(f"Model call rejected: {reason}")

        selected_model = model or self.primary_model
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient() as client:
            try:
                data = await self._execute_request(client, payload)
            except Exception as e:
                if self.fallback_model and selected_model != self.fallback_model:
                    logger.warning(f"Primary model {selected_model} failed with: {e}. Switching to fallback {self.fallback_model}")
                    payload["model"] = self.fallback_model
                    data = await self._execute_request(client, payload)
                    selected_model = self.fallback_model
                else:
                    raise

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        raw_content = msg.get("content")
        cleaned_content = strip_thinking_tags(raw_content)

        # Parse tool calls
        parsed_tool_calls: List[ToolCall] = []
        raw_tools = msg.get("tool_calls") or []
        for tc in raw_tools:
            tc_id = tc.get("id", "")
            func = tc.get("function", {})
            name = func.get("name", "")
            raw_args = func.get("arguments", "{}")
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse tool call arguments as JSON: {raw_args}")
                    args = {}
            else:
                args = raw_args or {}

            parsed_tool_calls.append(ToolCall(id=tc_id, name=name, arguments=args))

        # Extract usage and estimated cost
        usage = data.get("usage", {})
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)
        t_tokens = usage.get("total_tokens", p_tokens + c_tokens)

        # Record approximate cost ($0.15/1M tokens default estimate for open-weight models)
        est_cost = (t_tokens / 1_000_000) * 0.15
        budget_tracker.record_cost(est_cost)

        return LLMResponse(
            content=cleaned_content,
            tool_calls=parsed_tool_calls,
            model=data.get("model", selected_model),
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=t_tokens,
            estimated_cost_usd=est_cost,
            finish_reason=choice.get("finish_reason"),
        )
