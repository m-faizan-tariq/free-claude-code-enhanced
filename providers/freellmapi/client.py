"""FreeLLMAPI provider (OpenAI-compatible model router)."""

from __future__ import annotations

from typing import Any

from providers.base import ProviderConfig
from providers.defaults import FREELMAPI_DEFAULT_BASE
from providers.transports.openai_chat import OpenAIChatTransport

from .request import build_request_body


class FreeLLMAPIProvider(OpenAIChatTransport):
    """FreeLLMAPI at ``http://localhost:3001/v1/chat/completions``."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="FREELMAPI",
            base_url=config.base_url or FREELMAPI_DEFAULT_BASE,
            api_key=config.api_key,
        )

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return build_request_body(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
        )
