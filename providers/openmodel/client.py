"""OpenModel provider — Anthropic-compatible Messages at api.openmodel.ai/v1."""

from __future__ import annotations

from typing import Any

import httpx

from providers.base import ProviderConfig
from providers.defaults import OPENMODEL_DEFAULT_BASE
from providers.rotation import RotationConfig
from providers.transports.anthropic_messages import AnthropicMessagesTransport

_ANTHROPIC_VERSION = "2023-06-01"


class OpenModelProvider(AnthropicMessagesTransport):
    """OpenModel using ``https://api.openmodel.ai/v1/messages``."""

    def __init__(
        self,
        config: ProviderConfig,
        rotation_config: RotationConfig | None = None,
    ):
        super().__init__(
            config,
            provider_name="OPENMODEL",
            default_base_url=OPENMODEL_DEFAULT_BASE,
        )
        self._rotation_config = rotation_config or RotationConfig("[]")

    async def _validated_stream_send(
        self, body: dict, *, req_tag: str
    ) -> httpx.Response:
        pool_size = len(self._rotation_config._pool) if self._rotation_config.enabled else 1
        last_error: Exception | None = None
        for _ in range(pool_size):
            step = self._rotation_config.next_key() if self._rotation_config.enabled else None
            if step is not None:
                self._api_key = step.api_key
                # Do NOT recreate the httpx client — reusing the connection pool avoids
                # unnecessary TCP/TLS handshakes on every key rotation (which can cause
                # ReadError mid-stream when OpenModel doesn't expect new connections).
            try:
                response = await super()._validated_stream_send(body, req_tag=req_tag)
                if step is not None:
                    self._rotation_config.log_attempt(step, model=body.get("model", ""), provider="OpenModel", status=response.status_code)
                return response
            except Exception as exc:
                if step is not None:
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                        status_code = exc.response.status_code
                        self._rotation_config.log_attempt(step, model=body.get("model", ""), provider="OpenModel", status=status_code)
                        if status_code == 400:
                            try:
                                error_body = await exc.response.aread()
                                self._rotation_config.log_raw(step, f"400 body: {error_body.decode(errors='replace')[:2000]}")
                            except Exception:
                                pass
                    elif isinstance(exc, httpx.RequestError):
                        self._rotation_config.log_attempt(step, model=body.get("model", ""), provider="OpenModel", error="connection_error")
                    else:
                        self._rotation_config.log_attempt(step, model=body.get("model", ""), provider="OpenModel", error=f"{type(exc).__name__}")
                last_error = exc
                continue
        raise last_error

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return self._build_request_body_with_resolved_thinking(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
        )

    def _request_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "anthropic-version": _ANTHROPIC_VERSION,
        }

    def _model_list_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}
