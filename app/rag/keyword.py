from __future__ import annotations

import re
from typing import Any


class KeywordRetriever:
    def search(
        self,
        records: list[dict[str, Any]],
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not query.strip() or top_k <= 0:
            return []

        query_terms = self._tokenize(query)

        if not query_terms:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []

        for record in records:
            content = str(record.get("content", "")).strip()

            if not content:
                continue

            content_terms = self._tokenize(content)

            if not content_terms:
                continue

            matched_terms = query_terms.intersection(content_terms)

            if not matched_terms:
                continue

            score = len(matched_terms) / len(query_terms)

            scored.append(
                (
                    score,
                    record,
                )
            )

        scored.sort(
            key=lambda item: (
                -item[0],
                str(item[1].get("evidence_id", "")),
            )
        )

        results: list[dict[str, Any]] = []

        for score, record in scored[:top_k]:
            result = dict(record)
            result["keyword_score"] = round(score, 4)
            results.append(result)

        return results

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token.lower()
            for token in re.findall(r"\b[\w]+\b", text)
            if token
        }
