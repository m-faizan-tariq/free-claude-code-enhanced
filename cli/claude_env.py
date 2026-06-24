"""Shared Claude Code environment policy for FCC client surfaces."""

from __future__ import annotations

# No AUTO_COMPACT_WINDOW — the proxy advertises per-model context_window
# via /v1/models, so Claude Code auto-compacts at 80% of each model's limit.
CLAUDE_NO_AUTH_SENTINEL = "fcc-no-auth"


def claude_auth_token(auth_token: str) -> str:
    """Return the Claude Code auth marker for proxy-auth or no-auth sessions."""

    return auth_token.strip() or CLAUDE_NO_AUTH_SENTINEL
