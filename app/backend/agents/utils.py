"""Shared utilities for research agent nodes."""

from __future__ import annotations


def estimate_tokens(messages: list) -> int:
    """Rough token count from total message character length (~4 chars/token)."""
    return sum(len(str(getattr(m, "content", ""))) for m in messages) // 4
