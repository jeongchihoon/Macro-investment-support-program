"""Prompt text helpers shared across LLM stages."""
from __future__ import annotations

SUMMARY_PROMPT_CHAR_LIMIT = 1200
_BOUNDARIES = (".", "?", "!", "。", "？", "！", "\n")


def clip_for_prompt(text: str, limit: int = SUMMARY_PROMPT_CHAR_LIMIT) -> str:
    """Keep prompt context large enough for facts, but bounded and sentence-aware."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text

    clipped = text[:limit].rstrip()
    floor = int(limit * 0.6)
    cut_at = max(clipped.rfind(mark) for mark in _BOUNDARIES)
    if cut_at >= floor:
        return clipped[: cut_at + 1].strip()
    return clipped
