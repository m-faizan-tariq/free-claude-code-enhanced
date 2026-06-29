"""Multi-key rotation engine: round-robin key selection across configured keys."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import ClassVar

from loguru import logger

from config.rotation_settings import (
    mask_api_key,
    parse_api_keys_json,
)

# Sink is registered in config.logging_config.configure_logging() so it
# survives the logger.remove() call that happens during application startup.


@dataclass
class RotationStep:
    label: str
    api_key: str
    account_id: str = ""
    model: str | None = None


class RotationConfig:
    """Round-robin key rotation across a list of API keys.

    If ``single_key`` is provided and rotation is enabled (the list is
    non-empty), the single key is prepended to the rotation pool so that
    both the existing provider key and any rotation keys are cycled.
    """

    def __init__(self, api_keys_json: str, single_key: str = ""):
        entries = parse_api_keys_json(api_keys_json)
        keys_already = {e["api_key"] for e in entries}
        self._pool: list[RotationStep] = [
            RotationStep(
                label=e["label"],
                api_key=e["api_key"],
                account_id=e.get("account_id", ""),
            )
            for e in entries
        ]
        if single_key and self._pool and single_key not in keys_already:
            self._pool.insert(
                0,
                RotationStep(
                    label="Primary",
                    api_key=single_key,
                ),
            )
        self._cycle = itertools.cycle(self._pool) if self._pool else None

    @property
    def enabled(self) -> bool:
        return len(self._pool) > 0

    def next_key(self) -> RotationStep | None:
        """Return the next key (round-robin), or ``None`` if no keys configured."""
        if self._cycle is None:
            return None
        return next(self._cycle)

    _STATUS_LABELS: ClassVar[dict[int, str]] = {
        200: "OK",
        201: "OK",
        204: "OK",
        401: "unauthorized",
        403: "forbidden",
        429: "rate_limited",
        503: "unavailable",
    }

    def log_attempt(
        self,
        step: RotationStep | None,
        model: str = "",
        provider: str = "",
        status: int | None = None,
        error: str = "",
    ) -> None:
        """Log one rotation attempt with its outcome on a single line."""
        if step is None:
            return
        prov = f"[{provider}]" if provider else ""
        masked = mask_api_key(step.api_key)
        model_part = f" model={model or '?'}"
        if error:
            suffix = f" ✗ {error}"
        else:
            label = self._STATUS_LABELS.get(status or 0, "?")
            suffix = f" → {status} {label}"
        msg = f"{prov} key={step.label}{model_part} {masked}{suffix}"
        logger.bind(rotation=True).info(msg)

    def log_raw(self, step: RotationStep | None, msg: str, provider: str = "") -> None:
        """Log a raw diagnostic message associated with a rotation step."""
        if step is None:
            return
        prov = f"[{provider}]" if provider else ""
        masked = mask_api_key(step.api_key)
        logger.bind(rotation=True).info(f"{prov} key={step.label} {masked} {msg}")
