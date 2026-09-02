from __future__ import annotations

from app.state.evidence import EvidenceRecord


class EvidenceService:
    @staticmethod
    def build_evidence_document(evidence: list[EvidenceRecord]) -> list[dict]:
        return [record.model_dump() for record in evidence]
