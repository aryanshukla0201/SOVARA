from __future__ import annotations

from typing import Any


class ScoreNormalizer:
    @staticmethod
    def normalize(values: list[float]) -> list[float]:
        if not values:
            return []

        minimum = min(values)
        maximum = max(values)

        if maximum == minimum:
            return [0.5 for _ in values]

        return [
            (value - minimum) / (maximum - minimum)
            for value in values
        ]


class HybridScoreFusion:
    def __init__(
        self,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        if semantic_weight < 0 or keyword_weight < 0:
            raise ValueError("weights must be non-negative")

        if semantic_weight == 0 and keyword_weight == 0:
            raise ValueError("at least one weight must be positive")

        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

    def fuse(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candidates:
            return []

        total_weight = self.semantic_weight + self.keyword_weight

        semantic_values = [
            float(item.get("semantic_score", 0.0))
            for item in candidates
        ]
        keyword_values = [
            float(item.get("keyword_score", 0.0))
            for item in candidates
        ]

        semantic_normalized = ScoreNormalizer.normalize(semantic_values)
        keyword_normalized = ScoreNormalizer.normalize(keyword_values)

        for index, candidate in enumerate(candidates):
            semantic_score = semantic_values[index]
            keyword_score = keyword_values[index]

            candidate["semantic_score"] = semantic_score
            candidate["keyword_score"] = keyword_score

            candidate["semantic_score_normalized"] = semantic_normalized[index]
            candidate["keyword_score_normalized"] = keyword_normalized[index]

            candidate["legacy_hybrid_score"] = round(
                (
                    semantic_score * self.semantic_weight
                    + keyword_score * self.keyword_weight
                ) / total_weight,
                6,
            )

            candidate["hybrid_score"] = round(
                (
                    semantic_normalized[index] * self.semantic_weight
                    + keyword_normalized[index] * self.keyword_weight
                ) / total_weight,
                6,
            )

        return sorted(
            candidates,
            key=lambda item: (
                -float(item.get("hybrid_score", 0.0)),
                str(item.get("evidence_id", "")),
            ),
        )
