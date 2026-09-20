from __future__ import annotations

from typing import Any, Iterable

from app.state.evidence import EvidenceRecord


class EvidenceSelector:
    def select(
        self,
        candidates: Iterable[dict[str, Any]],
        top_k: int = 5,
    ) -> list[EvidenceRecord]:
        if top_k <= 0:
            return []

        best_by_id: dict[str, dict[str, Any]] = {}

        for candidate in candidates:
            evidence_id = candidate.get("evidence_id")

            if not evidence_id:
                continue

            key = str(evidence_id)

            score = self._score(candidate)

            existing = best_by_id.get(key)

            if existing is None or score > self._score(existing):
                best_by_id[key] = dict(candidate)

        ordered = sorted(
            best_by_id.values(),
            key=lambda item: (
                -self._score(item),
                str(item.get("evidence_id", "")),
            ),
        )

        selected: list[EvidenceRecord] = []

        for item in ordered[:top_k]:
            selected.append(
                EvidenceRecord(
                    evidence_id=str(item["evidence_id"]),
                    source_file_id=item.get("source_file_id"),
                    source_filename=item.get("source_filename"),
                    page_number=item.get("page_number"),
                    chunk_id=item.get("chunk_id"),
                    text=str(item.get("content", item.get("text", ""))),
                    relevance_score=self._score(item),
                    retrieval_method="hybrid_rag",
                )
            )

        return selected

    @staticmethod
    def _score(candidate: dict[str, Any]) -> float:
        if candidate.get("rerank_score") is not None:
            return float(candidate["rerank_score"])

        if candidate.get("hybrid_score") is not None:
            return float(candidate["hybrid_score"])

        return float(candidate.get("score", 0.0))
