"""Nous Portal (OpenAI-compatible Hermes proxy) adapter."""

from providers.defaults import NOUS_PORTAL_DEFAULT_BASE

from .client import NousPortalProvider

__all__ = ["NOUS_PORTAL_DEFAULT_BASE", "NousPortalProvider"]
