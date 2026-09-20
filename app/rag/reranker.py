from __future__ import annotations

from typing import Any


class ScoreReranker:
    """Deterministic reranker using existing retrieval signals."""

    def __init__(
        self,
        hybrid_weight: float = 0.6,
        keyword_weight: float = 0.25,
        semantic_weight: float = 0.15,
    ):
        weights = (
            hybrid_weight,
            keyword_weight,
            semantic_weight,
        )

        if any(weight < 0 for weight in weights):
            raise ValueError("reranker weights must be non-negative")

        if sum(weights) <= 0:
            raise ValueError(
                "at least one reranker weight must be positive"
            )

        self.hybrid_weight = hybrid_weight
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight

    def rerank(
        self,
        candidates: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not candidates or top_k <= 0:
            return []

        total_weight = (
            self.hybrid_weight
            + self.keyword_weight
            + self.semantic_weight
        )

        results = []

        for candidate in candidates:
            hybrid_score = float(
                candidate.get("hybrid_score", 0.0)
            )
            keyword_score = float(
                candidate.get("keyword_score", 0.0)
            )
            semantic_score = float(
                candidate.get("semantic_score", 0.0)
            )

            rerank_score = (
                (
                    self.hybrid_weight * hybrid_score
                    + self.keyword_weight * keyword_score
                    + self.semantic_weight * semantic_score
                )
                / total_weight
            )

            result = dict(candidate)
            result["rerank_score"] = round(
                rerank_score,
                4,
            )

            results.append(result)

        results.sort(
            key=lambda item: (
                -float(item["rerank_score"]),
                str(item.get("evidence_id", "")),
            )
        )

        return results[:top_k]
