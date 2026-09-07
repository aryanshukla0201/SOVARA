from __future__ import annotations

from typing import Any


class EvidenceNormalizer:
    @staticmethod
    def normalize(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []

        for index, item in enumerate(evidence, start=1):
            evidence_id = (
                item.get("evidence_id")
                or item.get("id")
                or f"evidence_{index:03d}"
            )

            content = (
                item.get("content")
                or item.get("text")
                or item.get("description")
                or ""
            )

            if not str(content).strip():
                continue

            normalized.append(
                {
                    "evidence_id": str(evidence_id),
                    "source_file_id": item.get("source_file_id"),
                    "source_filename": (
                        item.get("source_filename")
                        or item.get("filename")
                        or item.get("source_file")
                    ),
                    "evidence_type": (
                        item.get("evidence_type")
                        or item.get("type")
                        or "unknown"
                    ),
                    "content": str(content).strip(),
                    "confidence": item.get("confidence"),
                    "page_number": item.get("page_number"),
                    "chunk_id": item.get("chunk_id"),
                    "retrieval_method": (
                        item.get("retrieval_method")
                        or "unknown"
                    ),
                    "ocr_used": bool(
                        item.get("ocr_used", False)
                        or item.get("retrieval_method") == "pdf_ocr"
                    ),
                }
            )

        return normalized