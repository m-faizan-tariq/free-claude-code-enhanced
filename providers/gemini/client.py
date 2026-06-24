"""Google AI Studio Gemini provider (OpenAI-compatible chat completions)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from providers.base import ProviderConfig
from providers.defaults import GEMINI_DEFAULT_BASE
from providers.rotation import RotationConfig
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
        self._rotation_config = rotation_config or RotationConfig("[]")
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

    async def _create_stream(self, body: dict) -> tuple[Any, dict]:
        pool_size = (
            len(self._rotation_config._pool) if self._rotation_config.enabled else 1
        )
        last_error: Exception | None = None
        for _ in range(pool_size):
            step = (
                self._rotation_config.next_key()
                if self._rotation_config.enabled
                else None
            )
            if step is not None:
                self._api_key = step.api_key
                self._client.api_key = (
                    step.api_key
                )  # AsyncOpenAI stores key at construction; update it directly
            try:
                result = await super()._create_stream(body)
                if step is not None:
                    self._rotation_config.log_attempt(
                        step, model=body.get("model", ""), provider="Gemini", status=200
                    )
                return result
            except Exception as exc:
                if step is not None:
                    status = getattr(exc, "status_code", None)
                    if status is not None:
                        self._rotation_config.log_attempt(
                            step,
                            model=body.get("model", ""),
                            provider="Gemini",
                            status=status,
                        )
                    else:
                        self._rotation_config.log_attempt(
                            step,
                            model=body.get("model", ""),
                            provider="Gemini",
                            error=f"{type(exc).__name__}",
                        )
                last_error = exc
                continue
        if last_error is None:
            last_error = RuntimeError("all rotation attempts failed without exception")
        raise last_error

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return build_request_body(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
            tool_call_extra_content_by_id=self._tool_call_extra_content_by_id,
        )
