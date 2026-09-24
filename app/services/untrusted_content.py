from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class TrustClassification:
    trust_level: str
    content_origin: str
    instruction_like: bool
    reason: str


class UntrustedContentBoundary:
    """
    Classifies evidence crossing into SOVARA as data.

    This does not execute, remove, or rewrite content. It only annotates
    provenance/trust so downstream consumers can distinguish instructions
    contained inside external content from trusted application instructions.
    """

    _INSTRUCTION_PATTERNS = (
        r"\bignore\s+(?:all\s+)?previous\s+instructions\b",
        r"\bdisregard\s+(?:all\s+)?previous\s+instructions\b",
        r"\bforget\s+(?:all\s+)?previous\s+instructions\b",
        r"\bsystem\s+prompt\b",
        r"\bdeveloper\s+message\b",
        r"\bdo\s+not\s+follow\s+(?:the\s+)?instructions\b",
        r"\bexecute\s+(?:this|the)\s+(?:command|instruction)\b",
        r"\bcall\s+(?:this|the)\s+(?:tool|function)\b",
    )

    @classmethod
    def classify(
        cls,
        *,
        source_file_id: str | None = None,
        source_filename: str | None = None,
        retrieval_method: str | None = None,
        evidence_type: str | None = None,
        content: str = "",
    ) -> TrustClassification:
        external = bool(
            source_file_id
            or source_filename
            or retrieval_method
            in {
                "vector",
                "keyword",
                "hybrid",
                "pdf_ocr",
                "document",
                "retrieval",
            }
            or evidence_type in {"document", "retrieved", "external"}
        )

        instruction_like = any(
            re.search(pattern, content, flags=re.IGNORECASE)
            for pattern in cls._INSTRUCTION_PATTERNS
        )

        if external:
            reason = (
                "external_or_retrieved_content"
                if not instruction_like
                else "external_content_contains_instruction_like_text"
            )
            return TrustClassification(
                trust_level="untrusted",
                content_origin="external",
                instruction_like=instruction_like,
                reason=reason,
            )

        return TrustClassification(
            trust_level="trusted",
            content_origin="internal",
            instruction_like=instruction_like,
            reason=(
                "internal_content"
                if not instruction_like
                else "internal_content_contains_instruction_like_text"
            ),
        )

    @classmethod
    def annotate(cls, evidence: dict[str, Any]) -> dict[str, Any]:
        classification = cls.classify(
            source_file_id=evidence.get("source_file_id"),
            source_filename=evidence.get("source_filename"),
            retrieval_method=evidence.get("retrieval_method"),
            evidence_type=evidence.get("evidence_type"),
            content=str(evidence.get("content") or ""),
        )

        annotated = dict(evidence)
        annotated["trust_level"] = classification.trust_level
        annotated["content_origin"] = classification.content_origin
        annotated["instruction_like"] = classification.instruction_like
        annotated["trust_reason"] = classification.reason

        return annotated
