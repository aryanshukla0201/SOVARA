from __future__ import annotations

from typing import Any


class ScoreReranker:
    """Deterministic, replaceable local reranker boundary."""

    def __init__(
        self,
        hybrid_weight: float = 0.6,
        keyword_weight: float = 0.25,
        semantic_weight: float = 0.15,
    ):
        if (
            hybrid_weight < 0
            or keyword_weight < 0
            or semantic_weight < 0
        ):
            raise ValueError("weights must be non-negative")

        total = hybrid_weight + keyword_weight + semantic_weight
        if total <= 0:
            raise ValueError("at least one weight must be positive")

        self.hybrid_weight = hybrid_weight / total
        self.keyword_weight = keyword_weight / total
        self.semantic_weight = semantic_weight / total

    def rerank(
        self,
        query: str | list[dict[str, Any]],
        candidates: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        # Backward-compatible call shape: rerank(candidates, top_k=...).
        if isinstance(query, list):
            candidates = query
        if not candidates or top_k <= 0:
            return []

        results = []

        for item in candidates:
            result = dict(item)
            hybrid = float(result.get("hybrid_score", 0.0))
            keyword = float(result.get("keyword_score_normalized", result.get("keyword_score", 0.0)))
            semantic = float(result.get("semantic_score_normalized", result.get("semantic_score", 0.0)))

            result["rerank_score"] = round(
                self.hybrid_weight * hybrid
                + self.keyword_weight * keyword
                + self.semantic_weight * semantic,
                6,
            )
            results.append(result)

        results.sort(
            key=lambda item: (
                -float(item.get("rerank_score", 0.0)),
                str(item.get("evidence_id", "")),
            )
        )
        return results[:top_k]
