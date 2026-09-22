from __future__ import annotations

from typing import Any

from app.state.evidence import EvidenceRecord


class EvidenceSelector:
    def select(
        self,
        candidates: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[EvidenceRecord]:
        if top_k <= 0:
            return []

        best: dict[str, dict[str, Any]] = {}

        for candidate in candidates:
            evidence_id = str(candidate.get("evidence_id", "")).strip()
            if not evidence_id:
                continue

            score = float(
                candidate.get(
                    "rerank_score",
                    candidate.get(
                        "hybrid_score",
                        candidate.get("score", 0.0),
                    ),
                )
            )

            existing = best.get(evidence_id)
            if existing is None or score > float(
                existing.get(
                    "rerank_score",
                    existing.get(
                        "hybrid_score",
                        existing.get("score", 0.0),
                    ),
                )
            ):
                best[evidence_id] = candidate

        ordered = sorted(
            best.values(),
            key=lambda item: (
                -float(
                    item.get(
                        "rerank_score",
                        item.get(
                            "hybrid_score",
                            item.get("score", 0.0),
                        ),
                    )
                ),
                str(item.get("evidence_id", "")),
            ),
        )

        results: list[EvidenceRecord] = []

        for candidate in ordered[:top_k]:
            results.append(
                EvidenceRecord(
                    evidence_id=str(candidate["evidence_id"]),
                    source_file_id=candidate.get("source_file_id"),
                    source_filename=candidate.get("source_filename"),
                    page_number=candidate.get("page_number"),
                    chunk_id=candidate.get("chunk_id"),
                    document_id=candidate.get("document_id"),
                    section=candidate.get("section"),
                    text=str(candidate.get("content", candidate.get("text", ""))),
                    relevance_score=float(
                        candidate.get(
                            "rerank_score",
                            candidate.get(
                                "hybrid_score",
                                candidate.get("score", 0.0),
                            ),
                        )
                    ),
                    retrieval_score=(
                        float(candidate["semantic_score"])
                        if "semantic_score" in candidate
                        else float(candidate.get("score", 0.0))
                    ),
                    rerank_score=(
                        float(candidate["rerank_score"])
                        if "rerank_score" in candidate
                        else None
                    ),
                    retrieval_method=str(
                        candidate.get("retrieval_method", "hybrid_rag")
                    ),
                    provenance={
                        key: candidate[key]
                        for key in (
                            "source_file_id",
                            "source_filename",
                            "document_id",
                            "chunk_id",
                            "page_number",
                            "section",
                            "retrieval_method",
                        )
                        if candidate.get(key) is not None
                    },
                    citation_id=f"citation:{candidate['evidence_id']}",
                )
            )

        return results
