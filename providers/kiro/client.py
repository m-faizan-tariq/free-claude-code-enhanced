"""Kiro provider implementation (OpenAI-compatible chat completions via kiro-gateway)."""

from __future__ import annotations

from typing import Any

from providers.base import ProviderConfig
from providers.defaults import KIRO_DEFAULT_BASE
from providers.transports.openai_chat import OpenAIChatTransport

from .request import build_request_body


class KiroProvider(OpenAIChatTransport):
    """Kiro via kiro-gateway at ``http://localhost:8001/v1``."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="KIRO",
            base_url=config.base_url or KIRO_DEFAULT_BASE,
            api_key=config.api_key,
        )

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return build_request_body(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
        )
