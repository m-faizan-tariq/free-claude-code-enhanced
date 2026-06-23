"""Google AI Studio Gemini provider (OpenAI-compatible chat completions)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from httpx import Timeout
from loguru import logger
from openai import AsyncOpenAI

from providers.base import ProviderConfig
from providers.defaults import GEMINI_DEFAULT_BASE
from providers.rate_limit import retryable_upstream_status
from providers.rotation import RotationConfig, RotationStep
from providers.transports.openai_chat import OpenAIChatTransport

from .request import build_request_body

_MAX_TOOL_CALL_EXTRA_CONTENT_CACHE = 4096


class GeminiProvider(OpenAIChatTransport):
    """Gemini API using ``https://generativelanguage.googleapis.com/v1beta/openai/``."""

    def __init__(
        self,
        config: ProviderConfig,
        rotation_config: RotationConfig | None = None,
    ):
        super().__init__(
            config,
            provider_name="GEMINI",
            base_url=config.base_url or GEMINI_DEFAULT_BASE,
            api_key=config.api_key,
        )
        self._rotation_config = rotation_config or RotationConfig("[]", "[]")
        self._tool_call_extra_content_by_id: dict[str, dict[str, Any]] = {}

    def _record_tool_call_extra_content(
        self, tool_call_id: str, extra_content: dict[str, Any]
    ) -> None:
        if (
            tool_call_id not in self._tool_call_extra_content_by_id
            and len(self._tool_call_extra_content_by_id)
            >= _MAX_TOOL_CALL_EXTRA_CONTENT_CACHE
        ):
            self._tool_call_extra_content_by_id.pop(
                next(iter(self._tool_call_extra_content_by_id))
            )
        self._tool_call_extra_content_by_id[tool_call_id] = deepcopy(extra_content)

    def _create_client_for_step(self, step: RotationStep) -> AsyncOpenAI:
        """Create a new AsyncOpenAI client for a rotation step's API key."""
        return AsyncOpenAI(
            api_key=step.api_key,
            base_url=self._base_url,
            max_retries=0,
            timeout=Timeout(
                self._config.http_read_timeout,
                connect=self._config.http_connect_timeout,
                read=self._config.http_read_timeout,
                write=self._config.http_write_timeout,
            ),
        )

    async def _create_stream(self, body: dict) -> tuple[Any, dict]:
        steps = self._rotation_config.steps()
        if not steps:
            return await super()._create_stream(body)

        last_error: Exception | None = None
        for i, step in enumerate(steps):
            client = self._create_client_for_step(step)
            try:
                step_body = {**body, "model": step.model}
                create_body = self._prepare_create_body(step_body)
                stream = await self._global_rate_limiter.execute_with_retry(
                    client.chat.completions.create, **create_body, stream=True
                )
                return stream, step_body
            except Exception as exc:
                status = retryable_upstream_status(exc)
                if status is None:
                    raise
                last_error = exc
                self._rotation_config.log_rotation_attempt(step, i, len(steps))
                await client.close()
                continue

        raise last_error  # type: ignore[misc]

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return build_request_body(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
            tool_call_extra_content_by_id=self._tool_call_extra_content_by_id,
        )
