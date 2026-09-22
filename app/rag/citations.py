from __future__ import annotations

from typing import Any


class CitationBuilder:
    """Build deterministic source-to-evidence citation trace records."""

    @staticmethod
    def build(evidence: list[Any]) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []

        for item in evidence:
            evidence_id = getattr(item, "evidence_id", None)
            if not evidence_id:
                continue

            citations.append(
                {
                    "citation_id": f"citation:{evidence_id}",
                    "source_file_id": getattr(item, "source_file_id", None),
                    "source_filename": getattr(item, "source_filename", None),
                    "document_id": getattr(item, "document_id", None),
                    "chunk_id": getattr(item, "chunk_id", None),
                    "page_number": getattr(item, "page_number", None),
                    "section": getattr(item, "section", None),
                    "evidence_id": evidence_id,
                }
            )

        return citations
