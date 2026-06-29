"""Cloudflare Workers AI (OpenAI-compat) adapter."""

from providers.defaults import CLOUDFLARE_DEFAULT_BASE

from .client import CloudflareProvider

__all__ = ["CLOUDFLARE_DEFAULT_BASE", "CloudflareProvider"]
