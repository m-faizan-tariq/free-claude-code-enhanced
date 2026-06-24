# PRD: Multi-Key API Rotation for Gemini, OpenRouter, and OpenModel Providers

## Overview

Add multi-key round‑robin rotation to the Gemini, OpenRouter, and OpenModel
providers so that each request uses the next API key in sequence, balancing
load across multiple Google Cloud projects / OpenRouter accounts / OpenModel
keys. The Admin UI gains key management panels and a dedicated Rotation Chain
section for configuring ordered rotation with optional model overrides.

**Language convention:** Everywhere — spec, code comments, UI labels, commit
messages, docs — describe this as "key rotation" and "load balancing across
Google Cloud projects / OpenRouter accounts". Never use "bypass", "circumvent",
"get around", or "unlimited".

---

## Feature A: Multi-Key Gemini Rotation
_(OpenModel uses identical rotation mechanics — see Feature G)_

### Objectives
- Store N labeled Gemini API keys (each from a separate Google Cloud project).
- Round-robin across keys per-request: request N uses key N % len(keys).
- Rotate through `GEMINI_API_KEYS` directly (no chain).

### Success Criteria
- 2 keys configured; request 1 → key A, request 2 → key B, request 3 → key A.
- No keys configured → single-key path is identical to today.

### Data Structures
```json
GEMINI_API_KEYS = '[{"label":"Project A","api_key":"AIza..."},{"label":"Project B","api_key":"AIza..."}]'
```

---

## Feature B: Multi-Key OpenRouter Rotation

### Objectives
- Store N labeled OpenRouter API keys.
- Round-robin across keys per-request (same model as Feature A).

### Success Criteria
- 2 keys configured; request 1 → key A, request 2 → key B, request 3 → key A.
- No keys configured → single-key path is identical to today.

### Data Structures
```json
OPENROUTER_API_KEYS = '[{"label":"Account A","api_key":"sk-or-v1-..."}]'
```

---

## Feature C: Admin UI — Key Management Panels

### Sidebar
Nav item "Key Rotation" between "Providers" and "Model Config" in
`VIEW_GROUPS`.

### Content
Two sub-sections: "Gemini API Keys" and "OpenRouter API Keys".

Each shows:
- List of saved keys: [label] [masked key] [Remove]
- "+ Add Key" form: Label (text) + API Key (password) + Add button
- Description: "Add API keys from multiple Google Cloud projects / OpenRouter
  accounts for round‑robin rotation."

Keys are stored as a JSON array in the env file. Admin UI renders them with
per-key input fields and add/remove controls — no JSON editing required by the
user.

Existing `GEMINI_API_KEY` / `OPENROUTER_API_KEY` fields stay unchanged.

---



---

## Backward Compatibility Contract

- If `GEMINI_API_KEYS` is absent/empty, single `GEMINI_API_KEY` path is unchanged.
- If `OPENROUTER_API_KEYS` is absent/empty, single `OPENROUTER_API_KEY` path is
  unchanged.
- All existing providers, model-tier routing, Admin UI, and tests must pass
  unchanged.
- Provider base class (`BaseProvider.stream_response`) interface does NOT change.

---

## Security Rules

- API key values: NEVER in logs at any level. Log only `label=... key=...XXXX`.
- `ConfigurationError` raised for invalid JSON — safe message, no key value.
- Admin API responses mask api_key: `"...XXXX"` (last 4 chars).
- Input validation for non-empty labels and keys.

---

## Testing Strategy

### Unit Tests (Provider Level)
1. Round-robin: 2 keys, 3 requests → key1, key2, key1.
2. No keys configured → single-key path (regression).
3. Single key configured → same key returned every time.
4. No key values in log output (caplog).

### Config Tests
- JSON round-trip for all 4 new settings.
- Missing keys → no error, single-key path.
- Invalid JSON → ConfigurationError.

### Integration Tests (Admin API)
- Config fields present in API response.
- Apply/validate round-trips for key list fields.

### Validation Tests
- Missing label → structured error.
- Missing api_key → structured error.

### Regression
- All existing provider tests pass.
- All existing admin tests pass.
- Single-key path end-to-end.

---

## Out of Scope

- Error-based retry (rate limit retry is handled by the global rate limiter, not key rotation).
- External load balancer / API gateway.
- Exponential backoff per key (global rate limiter already does this).
- Features for any provider other than Gemini, OpenRouter, and OpenModel.
- Persistent key storage outside the existing env file mechanism.

### Objectives

Add the same round‑robin rotation pattern to the OpenModel Anthropic-compatible
provider, using identical rotation mechanics as Gemini/OpenRouter.

### Key Details

- Provider ID: ``openmodel``
- Transport: ``anthropic_messages`` (Anthropic Messages API at ``api.openmodel.ai/v1``)
- Model: ``deepseek-v4-flash`` (1M context, 8,192 max output)
- Auth: Bearer token (``om-...`` keys)
- Rotation env: ``OPENMODEL_API_KEYS`` (same JSON format as ``GEMINI_API_KEYS``)
- Admin section: ``openmodel_keys`` in the Key Rotation view group

### File Changes

| File | Change |
|------|--------|
| `providers/openmodel/client.py` | New — ``OpenModelProvider`` with rotation via ``_validated_stream_send`` |
| `providers/openmodel/__init__.py` | New — exports |
| `config/provider_catalog.py` | ``OPENMODEL_DEFAULT_BASE`` constant + ``openmodel`` descriptor |
| `config/defaults.py` | Re-export ``OPENMODEL_DEFAULT_BASE`` |
| `config/settings.py` | ``openmodel_api_key``, ``openmodel_api_keys``, ``openmodel_proxy`` fields |
| `providers/registry.py` | ``_create_openmodel`` factory with ``RotationConfig`` |
| `api/admin_config.py` | ``openmodel_keys`` section + ``OPENMODEL_API_KEY`` / ``OPENMODEL_API_KEYS`` fields |
| `api/admin_static/admin.js` | ``openmodel_keys`` in key_rotation view group; primary key mapping |
| `.env.example` | ``OPENMODEL_API_KEY``, ``OPENMODEL_API_KEYS``, ``OPENMODEL_PROXY`` |
| `tests/` | Provider order, registry mock, factory instantiation test |
| `docs/spec/001-multi-key-rotation-spec.md` | This section |

---

## Task Breakdown (13 slices)

---

## Task Breakdown (12 slices)

| # | Slice | Files | Commit |
|---|-------|-------|--------|
| 1 | Config — Gemini multi-key settings | `config/settings.py`, `.env.example` | `feat(config): add Gemini multi-key settings` |
| 2 | Config — OpenRouter multi-key settings | `config/settings.py`, `.env.example` | `feat(config): add OpenRouter multi-key settings` |
| 3 | Provider — Gemini rotation | `providers/gemini/client.py` | `feat(providers/gemini): multi-key rotation` |
| 4 | Provider — OpenRouter rotation | `providers/open_router/client.py` | `feat(providers/open_router): multi-key rotation` |
| 5 | Admin API — Gemini keys + chain | `api/admin_routes.py` | `feat(api): Gemini multi-key and fallback chain` |
| 6 | Admin API — OpenRouter keys + chain | `api/admin_routes.py` | `feat(api): OpenRouter multi-key and fallback chain` |
| 7 | Admin UI — Gemini key panel | `api/admin_static/admin.js`, `index.html` | `feat(admin-ui): Gemini key rotation panel` |
| 8 | Admin UI — OpenRouter key panel | `api/admin_static/admin.js`, `index.html` | `feat(admin-ui): OpenRouter key rotation panel` |
| 9 | Admin UI — Key management panels | `api/admin_static/admin.js`, `index.html`, `admin.css` | `feat(admin-ui): per-key add/remove UI` |
| 10 | Validation | `api/admin_config.py` | `feat(api): extend validation for multi-key settings` |
| 11 | Tests | `tests/` | `test: full coverage for multi-key rotation` |
| 12 | Docs | `docs/adr/`, `CHANGELOG.md` | `docs: ADR, CHANGELOG, docstrings` |
| 13 | OpenModel rotation | `providers/openmodel/`, `config/settings.py`, `config/provider_catalog.py`, `api/admin_config.py`, `api/admin_static/admin.js` | `feat(providers/openmodel): multi-key rotation` |
