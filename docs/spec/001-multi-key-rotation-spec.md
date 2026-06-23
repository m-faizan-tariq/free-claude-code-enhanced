# PRD: Multi-Key API Rotation for Gemini and OpenRouter Providers

## Overview

Add multi-key rotation (ordered fallback chain) to the Gemini and OpenRouter
providers so that when one API key's quota is exhausted (HTTP 429), the proxy
automatically rotates to the next key in the chain. The Admin UI gains key
management panels and a dedicated Fallback Chain section for configuring
rotation priority.

**Language convention:** Everywhere — spec, code comments, UI labels, commit
messages, docs — describe this as "key rotation" and "load balancing across
Google Cloud projects / OpenRouter accounts". Never use "bypass", "circumvent",
"get around", or "unlimited".

---

## Feature A: Multi-Key Gemini Rotation

### Objectives
- Store N labeled Gemini API keys (each from a separate Google Cloud project).
- On HTTP 429, iterate through the fallback chain in order.
- Each chain entry specifies a (model, key_label) pair; if key_label is
  `__default__`, use the existing single `GEMINI_API_KEY`.

### Success Criteria
- 2 keys in chain; key 1 → 429; key 2 → 200; request succeeds.
- All keys exhausted → caller sees a proper 429 error.
- No chain configured → single-key path is identical to today.

### Data Structures
```json
GEMINI_API_KEYS = '[{"label":"Project A","api_key":"AIza..."},{"label":"Project B","api_key":"AIza..."}]'
GEMINI_FALLBACK_CHAIN = '[{"label":"Primary","model":"gemini/models/gemini-3.1-flash-lite","key_label":"__default__"},{"label":"Backup A","model":"gemini/models/gemini-3.1-flash-lite","key_label":"Project A"}]'
```

---

## Feature B: Multi-Key OpenRouter Rotation

### Objectives
- Store N labeled OpenRouter API keys.
- On HTTP 429, iterate through the fallback chain in order.
- Each chain entry specifies a (model, key_label) pair; if key_label is
  `__default__`, use the existing single `OPENROUTER_API_KEY`.

### Success Criteria
- Same as Feature A but for OpenRouter (native Anthropic transport).
- All keys exhausted → caller sees proper 429.

### Data Structures
```json
OPENROUTER_API_KEYS = '[{"label":"Account A","api_key":"sk-or-v1-..."}]'
OPENROUTER_FALLBACK_CHAIN = '[{"label":"Primary","model":"open_router/models/some-model","key_label":"__default__"},{"label":"Backup","model":"open_router/models/some-model","key_label":"Account A"}]'
```

---

## Feature C: Admin UI — Key Management Panels

### Provider Section Changes

Gemini — new sub-section "Additional Gemini API Keys (Key Rotation)":
- List of saved keys: [label] [•••••••••XXXX] [Edit] [Remove]
- "+ Add Key" button → inline form with Label + password API Key input
- Existing GEMINI_API_KEY field stays unchanged
- Description: "Register API keys from multiple Google Cloud projects for
  automatic rotation. Each key should belong to a separate Google Cloud project."

OpenRouter — same pattern, sub-section "Additional OpenRouter API Keys (Key Rotation)".

### API Endpoints (per provider)
```
GET    /admin/providers/{provider}/keys
POST   /admin/providers/{provider}/keys       {label, api_key}
DELETE /admin/providers/{provider}/keys/{label}
PUT    /admin/providers/{provider}/keys/{label}  {label?, api_key?}
```

All responses mask api_key: `"...XXXX"` (last 4 chars only).

---

## Feature D: Admin UI — Fallback Chain Section

### Sidebar
New nav item "Fallback Chain" between "Providers" and "Model Config" in
`VIEW_GROUPS`.

### Content
Two sub-sections: "Gemini Rotation Chain" and "OpenRouter Rotation Chain".

Each shows:
- Ordered step list: [position] [label] [model] [key_label] [↑Up] [↓Down] [Remove]
- "+ Add Step" form: Label (text), Model (text, pre-filled), Key (dropdown from
  GET keys + "(Default) __default__")
- Up/Down calls PUT .../reorder with full reordered array
- Description: "When this provider's active key exhausts its quota, the proxy
  automatically rotates to the next step in this chain."

### API Endpoints (per provider)
```
GET    /admin/fallback-chain/{provider}
POST   /admin/fallback-chain/{provider}       {label, model, key_label}
DELETE /admin/fallback-chain/{provider}/{index}
PUT    /admin/fallback-chain/{provider}/reorder  [steps...]
```

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
1. Fallback chain: first key 429 → second key 200 → success.
2. Fallback chain: all keys 429 → rate-limit exception raised.
3. No chain configured: regression — single-key path.
4. Model override in chain entry.
5. No key values in log output (caplog).

### Config Tests
- JSON round-trip for all 4 new settings.
- Missing keys → no error, single-key fallback.
- Invalid JSON → ConfigurationError.

### Integration Tests (Admin API)
- CRUD for keys (create, read masked, update, delete).
- CRUD for fallback chain (create, read, delete by index, reorder).

### Validation Tests
- Invalid key_label → structured error.
- Wrong model prefix → structured error.
- Duplicate labels → structured error.

### Regression
- All existing provider tests pass.
- All existing admin tests pass.
- Single-key path end-to-end.

---

## Out of Scope

- Round-robin rotation (ordered chain only).
- External load balancer / API gateway.
- Exponential backoff per key (global rate limiter already does this).
- Features for any provider other than Gemini and OpenRouter.
- Persistent key storage outside the existing env file mechanism.

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
| 9 | Admin UI — Fallback Chain section | `api/admin_static/admin.js`, `index.html` | `feat(admin-ui): Fallback Chain sidebar section` |
| 10 | Validation | `api/admin_config.py` | `feat(api): extend validation for multi-key settings` |
| 11 | Tests | `tests/` | `test: full coverage for multi-key rotation` |
| 12 | Docs | `docs/adr/`, `CHANGELOG.md` | `docs: ADR, CHANGELOG, docstrings` |
