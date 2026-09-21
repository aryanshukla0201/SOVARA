from __future__ import annotations

from typing import Any


class ContextCompressor:
    """Deterministic context compressor compatible with token-budget controls."""

    def __init__(self, chars_per_token: int = 4):
        if chars_per_token <= 0:
            raise ValueError("chars_per_token must be positive")
        self.chars_per_token = chars_per_token

    def count_tokens(self, text: str) -> int:
        """Return the deterministic approximate token count used by compression."""
        if not text:
            return 0
        return max(
            1,
            (len(text) + self.chars_per_token - 1)
            // self.chars_per_token,
        )

    def compress_text(self, text: str, max_tokens: int) -> str:
        if not text or max_tokens <= 0:
            return ""

        max_chars = max_tokens * self.chars_per_token

        if len(text) <= max_chars:
            return text

        if max_chars <= 3:
            return "." * max_chars

        if max_chars <= 6:
            return text[: max_chars - 3] + "..."

        head = max_chars // 2
        tail = max_chars - head - 3
        return f"{text[:head]}...{text[-tail:]}"

    def compress(
        self,
        candidates: list[Any],
        max_context_tokens: int | None = None,
    ) -> list[Any]:
        if max_context_tokens is None or max_context_tokens <= 0:
            return candidates

        remaining = max_context_tokens
        result: list[Any] = []

        for item in candidates:
            text = getattr(item, "text", None)
            if text is None and isinstance(item, dict):
                text = item.get("content", "")

            available_tokens = max(1, remaining)
            compressed = self.compress_text(str(text or ""), available_tokens)

            if hasattr(item, "text"):
                item = item.model_copy(update={"text": compressed})
            else:
                item = dict(item)
                item["content"] = compressed

            result.append(item)
            used = max(1, (len(compressed) + self.chars_per_token - 1) // self.chars_per_token)
            remaining -= used

            if remaining <= 0:
                break

        return result
