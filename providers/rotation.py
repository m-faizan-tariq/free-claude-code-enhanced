"""Multi-key rotation engine: resolves fallback chain steps from config."""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from config.rotation_settings import (
    mask_api_key,
    parse_api_keys_json,
    parse_rotation_chain_json,
)


@dataclass
class RotationStep:
    label: str
    model: str
    key_label: str
    api_key: str


class RotationConfig:
    """Parsed multi-key rotation config with key resolution."""

    def __init__(self, api_keys_json: str, chain_json: str):
        self.api_keys = parse_api_keys_json(api_keys_json)
        self.chain = parse_rotation_chain_json(chain_json)
        self._key_map: dict[str, str] = {
            entry["label"]: entry["api_key"] for entry in self.api_keys
        }

    @property
    def enabled(self) -> bool:
        return len(self.chain) > 0

    def resolve_key(self, key_label: str) -> str | None:
        return self._key_map.get(key_label)

    def _model_id_only(self, full_model: str) -> str:
        """Strip provider prefix from 'provider/model/name' → 'model/name'."""
        parts = full_model.split("/", 1)
        return parts[1] if len(parts) > 1 else parts[0]

    def steps(self) -> list[RotationStep]:
        """Return resolved chain steps with api_key and model_id."""
        resolved: list[RotationStep] = []
        for i, entry in enumerate(self.chain):
            api_key = self._key_map.get(entry["key_label"])
            if api_key is None:
                logger.warning(
                    "Rotation chain step {}: key_label={} not found in API keys",
                    i,
                    entry["key_label"],
                )
                continue
            resolved.append(
                RotationStep(
                    label=entry["label"],
                    model=self._model_id_only(entry["model"]),
                    key_label=entry["key_label"],
                    api_key=api_key,
                )
            )
        return resolved

    def log_rotation_attempt(self, step: RotationStep, attempt: int, total: int) -> None:
        """Log a rotation attempt with masked key."""
        logger.warning(
            "Rotation attempt {}/{}: label={} key={} model={}",
            attempt + 1,
            total,
            step.label,
            mask_api_key(step.api_key),
            step.model,
        )
