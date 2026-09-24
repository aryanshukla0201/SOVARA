from __future__ import annotations

import re


class QueryRewriter:
    """Deterministic retrieval-query normalization.

    The original user query is never replaced at the orchestration layer.
    Rewriting is retrieval-only and intentionally produces no new facts.
    """

    def rewrite(self, query: str) -> str:
        if not query or not query.strip():
            return ""
        return re.sub(r"\s+", " ", query.strip().lower())

    def rewrite_queries(self, query: str) -> list[str]:
        original = query.strip() if query else ""
        if not original:
            return []
        rewritten = self.rewrite(original)
        if not rewritten or rewritten == original:
            return [original]
        return [original, rewritten]
