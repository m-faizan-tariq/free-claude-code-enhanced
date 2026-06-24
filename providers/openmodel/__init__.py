"""OpenModel provider — Anthropic-compatible Messages API."""

from providers.defaults import OPENMODEL_DEFAULT_BASE

from .client import OpenModelProvider

__all__ = ["OPENMODEL_DEFAULT_BASE", "OpenModelProvider"]
