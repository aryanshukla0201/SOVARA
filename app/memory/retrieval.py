from __future__ import annotations

import re

from app.memory.models import MemoryRecord


class MemoryRetriever:
    def search(
        self,
        memories: list[MemoryRecord],
        query: str,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        if not query.strip() or limit <= 0:
            return []

        query_terms = self._tokenize(query)

        if not query_terms:
            return []

        scored: list[tuple[float, MemoryRecord]] = []

        for memory in memories:
            content_terms = self._tokenize(memory.content)

            if not content_terms:
                continue

            matched_terms = query_terms.intersection(content_terms)

            if not matched_terms:
                continue

            score = len(matched_terms) / len(query_terms)
            scored.append((score, memory))

        scored.sort(
            key=lambda item: (
                -item[0],
                -item[1].updated_at.timestamp(),
                item[1].memory_id,
            )
        )

        return [memory for _, memory in scored[:limit]]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token.lower()
            for token in re.findall(r"\b[\w]+\b", text)
            if token
        }
