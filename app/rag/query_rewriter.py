from __future__ import annotations

import re


class QueryRewriter:
    """Deterministic query normalization for RAG retrieval."""

    _WHITESPACE_RE = re.compile(r"\s+")

    def rewrite(self, query: str) -> str:
        if not query or not query.strip():
            return ""

        normalized = query.strip().lower()
        normalized = self._WHITESPACE_RE.sub(" ", normalized)

        return normalized
