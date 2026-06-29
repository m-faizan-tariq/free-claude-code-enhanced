"""Cloudflare Workers AI provider (OpenAI-compatible chat completions)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx
from openai import AsyncOpenAI

from core.anthropic import build_base_request_body
from providers.base import ProviderConfig, ProviderModelInfo
from providers.defaults import CLOUDFLARE_DEFAULT_BASE
from providers.rotation import RotationConfig
from providers.transports.openai_chat import OpenAIChatTransport

_CHAT_TASK_NAMES = frozenset(
    {
        "text generation",
    }
)


def _build_cloudflare_url(account_id: str) -> str:
    """Build the base URL from an account ID."""
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"


class CloudflareProvider(OpenAIChatTransport):
    """Cloudflare Workers AI using ``https://api.cloudflare.com/client/v4/accounts/{id}/ai/v1``."""

    def __init__(
        self,
        config: ProviderConfig,
        rotation_config: RotationConfig | None = None,
        account_id: str = "",
    ):
        base_url = (
            _build_cloudflare_url(account_id)
            if account_id
            else config.base_url or CLOUDFLARE_DEFAULT_BASE
        )
        super().__init__(
            config,
            provider_name="CLOUDFLARE",
            base_url=base_url,
            api_key=config.api_key,
        )
        self._rotation_config = rotation_config or RotationConfig("[]")
        self._account_id = account_id

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return build_base_request_body(request)

    async def list_model_ids(self) -> frozenset[str]:
        """Discover chat models via Cloudflare's models/search endpoint."""
        if not self._account_id:
            return frozenset()
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self._account_id}/ai/models/search"
        )
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            body = response.json()
        models: Sequence[dict[str, Any]] = body.get("result") or []
        chat_models: list[str] = []
        for model in models:
            name: str = (model.get("name") or "").strip()
            task: dict[str, Any] | None = model.get("task")
            if not name:
                continue
            if task and isinstance(task, dict):
                task_name = (task.get("name") or "").strip().lower()
                if task_name and task_name not in _CHAT_TASK_NAMES:
                    continue
            chat_models.append(name)
        return frozenset(chat_models)

    async def list_model_infos(self) -> frozenset[ProviderModelInfo]:
        ids = await self.list_model_ids()
        return frozenset(
            ProviderModelInfo(model_id=mid, supports_thinking=True) for mid in ids
        )

    def _apply_step(self, step: Any) -> None:
        self._api_key = step.api_key
        self._client.api_key = step.api_key
        if step.account_id and step.account_id != self._account_id:
            self._account_id = step.account_id
            base_url = _build_cloudflare_url(self._account_id)
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=base_url,
                max_retries=0,
                timeout=self._client._client._timeout,
            )

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
                self._apply_step(step)
            try:
                result = await super()._create_stream(body)
                if step is not None:
                    self._rotation_config.log_attempt(
                        step,
                        model=body.get("model", ""),
                        provider="Cloudflare",
                        status=200,
                    )
                return result
            except Exception as exc:
                if step is not None:
                    status = getattr(exc, "status_code", None)
                    if status is not None:
                        self._rotation_config.log_attempt(
                            step,
                            model=body.get("model", ""),
                            provider="Cloudflare",
                            status=status,
                        )
                    else:
                        self._rotation_config.log_attempt(
                            step,
                            model=body.get("model", ""),
                            provider="Cloudflare",
                            error=f"{type(exc).__name__}",
                        )
                last_error = exc
                continue
        if last_error is None:
            last_error = RuntimeError("all rotation attempts failed without exception")
        raise last_error
