from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DocumentFactResult:
    success: bool
    answer: str = ""
    evidence_id: str | None = None
    field: str | None = None


class DocumentFactExtractor:
    """
    Deterministic extraction for simple labeled document facts.

    This is intentionally narrow:
    - It handles exact fact questions where the document contains
      an explicit label followed by a value.
    - It does NOT attempt general document reasoning.
    - Complex questions continue through ReasoningNode.
    """

    FIELD_PATTERNS: dict[str, list[str]] = {
        "problem_statement_id": [
            r"\bproblem\s+statement\s+id\b",
            r"\bps\s+id\b",
        ],
        "problem_statement_title": [
            r"\bproblem\s+statement\s+title\b",
            r"\bps\s+title\b",
        ],
        "team_id": [
            r"\bteam\s+id\b",
        ],
        "team_name": [
            r"\bteam\s+name\b",
        ],
        "theme": [
            r"\btheme\b",
        ],
        "ps_category": [
            r"\bps\s+category\b",
            r"\bproblem\s+statement\s+category\b",
        ],
    }

    # Ordered longest-first because some labels contain others.
    FIELD_ORDER = [
        "problem_statement_title",
        "problem_statement_id",
        "ps_category",
        "team_name",
        "team_id",
        "theme",
    ]

    FIELD_LABELS: dict[str, str] = {
        "problem_statement_id": "Problem Statement ID",
        "problem_statement_title": "Problem Statement Title",
        "team_id": "Team ID",
        "team_name": "Team Name",
        "theme": "Theme",
        "ps_category": "PS Category",
    }

    @classmethod
    def detect_field(cls, query: str) -> str | None:
        """
        Detect whether the user is asking for one or more exact
        labeled document fields.

        Only a single-field extraction is handled here.
        Compound questions remain on the normal reasoning path.
        """
        normalized = query.strip().lower()

        matches: list[str] = []

        for field in cls.FIELD_ORDER:
            for pattern in cls.FIELD_PATTERNS[field]:
                if re.search(pattern, normalized):
                    matches.append(field)
                    break

        if len(matches) != 1:
            return None

        # Make sure this looks like a request for the value,
        # rather than a general discussion involving the field.
        extraction_markers = [
            "what is",
            "what's",
            "give me",
            "tell me",
            "provide",
            "which is",
            "state",
            "identify",
        ]

        if not any(marker in normalized for marker in extraction_markers):
            return None

        return matches[0]

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        """
        Normalize PDF extraction artifacts without changing
        meaningful content.
        """
        text = text.replace("\u2013", "-")
        text = text.replace("\u2014", "-")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def _extract_labeled_value(
        cls,
        text: str,
        field: str,
    ) -> str | None:
        """
        Extract the value following a known document label.

        Handles common PDF extraction variants such as:
            Label – Value
            Label - Value
            Label: Value
            Label Value

        The value ends at the next known document label.
        """
        text = cls._normalize_text(text)

        label = cls.FIELD_LABELS[field]

        # Locate the requested label.
        label_match = re.search(
            re.escape(label),
            text,
            flags=re.IGNORECASE,
        )

        if not label_match:
            return None

        value_start = label_match.end()

        # Everything after the requested label.
        remainder = text[value_start:]

        # Remove the separator between label and value.
        remainder = re.sub(
            r"^\s*[-:?\u2013\u2014]+\s*",
            "",
            remainder,
        )

        # Find the earliest occurrence of another known label.
        next_label_positions: list[int] = []

        for other_field in cls.FIELD_ORDER:
            if other_field == field:
                continue

            other_label = cls.FIELD_LABELS[other_field]

            match = re.search(
                rf"\b{re.escape(other_label)}\b",
                remainder,
                flags=re.IGNORECASE,
            )

            if match:
                next_label_positions.append(match.start())

        if next_label_positions:
            value = remainder[
                : min(next_label_positions)
            ]
        else:
            value = remainder

        value = value.strip()

        # Remove common trailing PDF artifacts.
        value = re.sub(
            r"\s+(?:TITLE PAGE|TECHNICAL APPROACH)\s*$",
            "",
            value,
            flags=re.IGNORECASE,
        )

        return value.strip(" -:;,.") or None

    @classmethod
    def extract(
        cls,
        query: str,
        evidence: list[dict],
    ) -> DocumentFactResult:
        field = cls.detect_field(query)

        if field is None:
            return DocumentFactResult(success=False)

        # Prefer the highest-relevance evidence first.
        candidates = sorted(
            [
                item
                for item in evidence
                if isinstance(item, dict)
                and item.get("content")
            ],
            key=lambda item: float(
                item.get("relevance_score") or 0.0
            ),
            reverse=True,
        )

        for item in candidates:
            value = cls._extract_labeled_value(
                item["content"],
                field,
            )

            if value:
                evidence_id = item.get("evidence_id")

                citation = (
                    f" [{evidence_id}]"
                    if evidence_id
                    else ""
                )

                answer = (
                    f"{cls.FIELD_LABELS[field]}: "
                    f"{value}{citation}"
                )

                return DocumentFactResult(
                    success=True,
                    answer=answer,
                    evidence_id=(
                        str(evidence_id)
                        if evidence_id
                        else None
                    ),
                    field=field,
                )

        return DocumentFactResult(
            success=False,
            field=field,
        )