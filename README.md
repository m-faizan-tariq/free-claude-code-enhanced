# Free Claude Code — Enhanced Fork

Multi-key rotation, transport resilience, and OpenModel support on top of [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code).

## What's Different

| Feature | Original | This Fork |
|---|---|---|
| Multi-key rotation & fallback | One key per provider | N keys, round-robin, auto-fallback on 400/401/429/503/connection errors |
| OpenModel provider | Not supported | `openmodel/deepseek-v4-flash` and other models via `api.openmodel.ai/v1/messages` |
| Mid-stream transport retry | Drops stream on ReadError | Retries full request with next key (up to 3x) |
| Tool_use orphan stripping | — | Strips orphan tool_use blocks that cause HTTP 400 |
| Connection pool on rotation | Recreates TCP connection per retry | Reuses pool — eliminates ReadError from TCP churn |
| Diagnostic logging | — | Logs 400 response bodies to rotation log |

## Install

```bash
curl -fsSL "https://github.com/m-faizan-tariq/free-claude-code-enhanced/blob/main/scripts/install.sh?raw=1" | sh
```

Or from source:
```bash
git clone https://github.com/m-faizan-tariq/free-claude-code-enhanced.git
cd free-claude-code-enhanced
uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

## Quick Config

1. Run `fcc-server` — opens Admin UI at `http://127.0.0.1:8082/admin`
2. Add API keys for your chosen providers
3. Run your client:
   - Claude Code: `fcc-claude`
   - Codex: `fcc-codex`

## Multi-Key Setup

In Admin UI → provider config, set the `_API_KEYS` field to a JSON array:

```json
[
  {"label": "key-1", "api_key": "sk-..."},
  {"label": "key-2", "api_key": "sk-..."}
]
```

The proxy cycles keys round-robin. If one fails, the next is tried automatically. Supported for OpenModel, OpenRouter, and Gemini providers.

## Providers

All 18 providers are configured through the Admin UI. Set `MODEL` to a provider-prefixed slug:
- `openmodel/deepseek-v4-flash`
- `nvidia_nim/nvidia/nemotron-3-super-120b-a12b`
- `open_router/openrouter/free`
- `gemini/models/gemini-3.1-flash-lite`
- `deepseek/deepseek-chat`
- `mistral/devstral-small-latest`
- `mistral_codestral/codestral-latest`
- `opencode/gpt-5.3-codex`
- `opencode_go/minimax-m2.7`
- `wafer/DeepSeek-V4-Pro`
- `kimi/kimi-k2.5`
- `cerebras/llama3.1-8b`
- `groq/llama-3.3-70b-versatile`
- `fireworks/accounts/fireworks/models/llama-v3p3-70b-instruct`
- `zai/glm-5.1`
- `lmstudio/<model-id>`
- `llamacpp/<model-name>`
- `ollama/llama3.1`

## Credit

This is a fork of [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code) — all the core proxy infrastructure, provider adapters, Admin UI, and client launchers are their work. This fork only adds the features listed above.

## License

MIT. See [LICENSE](LICENSE).
