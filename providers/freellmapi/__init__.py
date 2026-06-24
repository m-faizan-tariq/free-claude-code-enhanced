"""FreeLLMAPI (OpenAI-compatible model router) adapter."""

from providers.defaults import FREELMAPI_DEFAULT_BASE

from .client import FreeLLMAPIProvider

__all__ = ["FREELMAPI_DEFAULT_BASE", "FreeLLMAPIProvider"]
