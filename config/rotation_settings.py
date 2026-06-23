"""Multi-key rotation settings: API key lists and fallback chains."""

import json
from typing import Any


def validate_rotation_api_keys_json(value: str) -> str:
    """Validate a JSON-encoded list of ``{label, api_key}`` entries.

    Returns the original string on success. Raises ``ValueError`` with a
    safe message (no key content) on failure.
    """
    parsed = _parse_json_safe(value, "API key list")
    if not isinstance(parsed, list):
        raise ValueError("GEMINI_API_KEYS must be a JSON list")
    if not parsed:
        return value
    for i, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {i} in API key list must be an object")
        label = entry.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Entry {i}: 'label' must be a non-empty string")
        api_key = entry.get("api_key")
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError(f"Entry {i}: 'api_key' must be a non-empty string")
    return value


def validate_rotation_chain_json(value: str) -> str:
    """Validate a JSON-encoded list of ``{label, model, key_label}`` entries.

    Returns the original string on success. Raises ``ValueError`` with a
    safe message on failure.
    """
    parsed = _parse_json_safe(value, "rotation chain")
    if not isinstance(parsed, list):
        raise ValueError("Rotation chain must be a JSON list")
    if not parsed:
        return value
    for i, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            raise ValueError(f"Chain entry {i} must be an object")
        label = entry.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Chain entry {i}: 'label' must be a non-empty string")
        model = entry.get("model")
        if not isinstance(model, str) or not model.strip():
            raise ValueError(f"Chain entry {i}: 'model' must be a non-empty string")
        key_label = entry.get("key_label")
        if not isinstance(key_label, str) or not key_label.strip():
            raise ValueError(
                f"Chain entry {i}: 'key_label' must be a non-empty string"
            )
    return value


def parse_api_keys_json(value: str) -> list[dict[str, str]]:
    """Parse a validated API keys JSON string into a Python list."""
    if not value or value == "[]":
        return []
    return _parse_json_safe(value, "API key list")


def parse_rotation_chain_json(value: str) -> list[dict[str, str]]:
    """Parse a validated rotation chain JSON string into a Python list."""
    if not value or value == "[]":
        return []
    return _parse_json_safe(value, "rotation chain")


def _parse_json_safe(value: str, label: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {label}: {exc}") from exc


def mask_api_key(api_key: str) -> str:
    """Return a masked version of an API key showing only the last 4 chars."""
    if not api_key or len(api_key) < 4:
        return "••••"
    return "••••••••" + api_key[-4:]


def safe_key_log(label: str, api_key: str) -> str:
    """Return a safe log string with label and masked key."""
    return f"label={label}, key={mask_api_key(api_key)}"
