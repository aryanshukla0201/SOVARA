from __future__ import annotations

import re
from typing import Any


class EvidenceDiversity:
    """Remove duplicate chunks while keeping relevance as the primary signal."""

    @staticmethod
    def _text_key(text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip().lower())

    def select(self, candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        selected: list[dict[str, Any]] = []
        seen_chunk_keys: set[str] = set()
        seen_text_keys: set[str] = set()

        for candidate in candidates:
            evidence_id = str(candidate.get("evidence_id", "")).strip()
            if not evidence_id:
                continue

            source_file_id = candidate.get("source_file_id")
            chunk_id = candidate.get("chunk_id")
            text_key = self._text_key(candidate.get("content", candidate.get("text", "")))

            if source_file_id is not None and chunk_id is not None:
                chunk_key = f"{source_file_id}::{chunk_id}"
            else:
                chunk_key = ""

            if chunk_key and chunk_key in seen_chunk_keys:
                continue
            if text_key and text_key in seen_text_keys:
                continue

            selected.append(candidate)
            if chunk_key:
                seen_chunk_keys.add(chunk_key)
            if text_key:
                seen_text_keys.add(text_key)

            if len(selected) >= limit:
                break

        return selected
