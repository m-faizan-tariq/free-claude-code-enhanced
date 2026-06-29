"""Kiro (via kiro-gateway) OpenAI-compatible adapter."""

from providers.defaults import KIRO_DEFAULT_BASE

from .client import KiroProvider

__all__ = ["KIRO_DEFAULT_BASE", "KiroProvider"]
