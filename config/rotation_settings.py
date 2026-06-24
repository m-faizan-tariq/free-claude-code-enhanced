"""Multi-key rotation settings: API key lists and fallback chains."""

import json
from typing import Any


def validate_rotation_api_keys_json(value: str) -> str:
    """Validate a JSON-encoded list of ``{label, api_key}`` entries.

    Accepts both ``"api_key"`` and ``"key"`` as the credential field name
    (backward compatibility with older configs).

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
        api_key = entry.get("api_key") or entry.get("key")
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError(f"Entry {i}: 'api_key' must be a non-empty string")
    return value



def parse_api_keys_json(value: str) -> list[dict[str, str]]:
    """Parse a validated API keys JSON string into a Python list.

    Normalises the old ``"key"`` field name to ``"api_key"`` for
    backward compatibility.
    """
    if not value or value == "[]":
        return []
    entries = _parse_json_safe(value, "API key list")
    for entry in entries:
        if "key" in entry and "api_key" not in entry:
            entry["api_key"] = entry.pop("key")
    return entries



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
