"""Model-list response construction for Claude-compatible clients."""

from __future__ import annotations

from config.settings import Settings
from providers.registry import ProviderRegistry

from .gateway_model_ids import gateway_model_id
from .models.responses import ModelResponse, ModelsListResponse

DISCOVERED_MODEL_CREATED_AT = "1970-01-01T00:00:00Z"

_KNOWN_CONTEXT_LIMITS: dict[str, int] = {
    "deepseek-v4-flash": 1_048_576,
    "deepseek-v4-flash-free": 1_048_576,
    "stepfun-ai/step-3.7-flash": 131_072,
    "step-3.7-flash": 131_072,
    "nvidia/nemotron-3-super-120b-a12b": 131_072,
    "gemini-3.1-flash-lite": 1_048_576,
    "gemini-3-flash-preview": 1_048_576,
    "kimi-k2.5": 131_072,
    "kimi-k2.6": 131_072,
    "glm-5.1": 131_072,
    "glm-5-turbo": 131_072,
    "llama-3.3-70b-versatile": 131_072,
    "llama3.1-8b": 131_072,
    "llama3.1": 131_072,
    "qwen3.5-coder": 131_072,
    "qwen3.5-397b-a17b": 131_072,
    "minimax-m2.5": 1_048_576,
    "minimax-m2.7": 1_048_576,
}

_CONTEXT_LIMITS_BY_ID: dict[str, int] = {}
_CONTEXT_LIMITS_INITIALIZED = False


def _init_context_limits() -> None:
    global _CONTEXT_LIMITS_BY_ID, _CONTEXT_LIMITS_INITIALIZED
    for key, ctx in _KNOWN_CONTEXT_LIMITS.items():
        _CONTEXT_LIMITS_BY_ID[key] = ctx
        for prefix in (
            "nvidia_nim/",
            "openmodel/",
            "gemini/models/",
            "open_router/",
            "kimi/",
            "zai/",
            "groq/",
            "cerebras/",
            "lmstudio/",
            "llamacpp/",
            "ollama/",
            "wafer/",
        ):
            _CONTEXT_LIMITS_BY_ID[f"{prefix}{key}"] = ctx
    _CONTEXT_LIMITS_INITIALIZED = True


def _context_window_for(model_id: str) -> int | None:
    if not _CONTEXT_LIMITS_INITIALIZED:
        _init_context_limits()
    return _CONTEXT_LIMITS_BY_ID.get(model_id)


SUPPORTED_CLAUDE_MODELS = [
    ModelResponse(
        id="claude-opus-4-20250514",
        display_name="Claude Opus 4",
        created_at="2025-05-14T00:00:00Z",
    ),
    ModelResponse(
        id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        created_at="2025-05-14T00:00:00Z",
    ),
    ModelResponse(
        id="claude-haiku-4-20250514",
        display_name="Claude Haiku 4",
        created_at="2025-05-14T00:00:00Z",
    ),
    ModelResponse(
        id="claude-3-opus-20240229",
        display_name="Claude 3 Opus",
        created_at="2024-02-29T00:00:00Z",
    ),
    ModelResponse(
        id="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        created_at="2024-10-22T00:00:00Z",
    ),
    ModelResponse(
        id="claude-3-haiku-20240307",
        display_name="Claude 3 Haiku",
        created_at="2024-03-07T00:00:00Z",
    ),
    ModelResponse(
        id="claude-3-5-haiku-20241022",
        display_name="Claude 3.5 Haiku",
        created_at="2024-10-22T00:00:00Z",
    ),
]


def build_models_list_response(
    settings: Settings, provider_registry: ProviderRegistry | None
) -> ModelsListResponse:
    """Return configured, cached, and compatibility model ids."""
    models: list[ModelResponse] = []
    seen: set[str] = set()

    for ref in settings.configured_chat_model_refs():
        supports_thinking = None
        if provider_registry is not None:
            supports_thinking = provider_registry.cached_model_supports_thinking(
                ref.provider_id, ref.model_id
            )
        _append_provider_model_variants(
            models,
            seen,
            ref.model_ref,
            supports_thinking=supports_thinking,
        )

    if provider_registry is not None:
        for model_info in provider_registry.cached_prefixed_model_infos():
            _append_provider_model_variants(
                models,
                seen,
                model_info.model_id,
                supports_thinking=model_info.supports_thinking,
            )

    for model in SUPPORTED_CLAUDE_MODELS:
        _append_unique_model(models, seen, model)

    return ModelsListResponse(
        data=models,
        first_id=models[0].id if models else None,
        has_more=False,
        last_id=models[-1].id if models else None,
    )


def _discovered_model_response(model_id: str, *, display_name: str) -> ModelResponse:
    return ModelResponse(
        id=model_id,
        display_name=display_name,
        created_at=DISCOVERED_MODEL_CREATED_AT,
        context_window=_context_window_for(model_id),
    )


def _append_unique_model(
    models: list[ModelResponse], seen: set[str], model: ModelResponse
) -> None:
    if model.id in seen:
        return
    seen.add(model.id)
    models.append(model)


def _append_provider_model_variants(
    models: list[ModelResponse],
    seen: set[str],
    provider_model_ref: str,
    *,
    supports_thinking: bool | None = None,
) -> None:
    _append_unique_model(
        models,
        seen,
        _discovered_model_response(
            gateway_model_id(provider_model_ref),
            display_name=provider_model_ref,
        ),
    )
