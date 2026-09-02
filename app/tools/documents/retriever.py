from __future__ import annotations

import re

from app.state.evidence import EvidenceRecord


class DocumentRetriever:
    def __init__(self, top_k: int = 5, min_score: float = 0.05):
        self.top_k = top_k
        self.min_score = min_score

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """
        Convert text into normalized tokens.

        This intentionally uses a simple deterministic tokenizer.
        It can later be replaced with embedding-based retrieval
        without changing DocumentNode or EvidenceRecord.
        """

        tokens = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())

        return {
            token
            for token in tokens
            if len(token) > 2
        }

    def _score_chunk(
        self,
        query_tokens: set[str],
        chunk_tokens: set[str],
    ) -> float:

        if not query_tokens or not chunk_tokens:
            return 0.0

        overlap = query_tokens.intersection(chunk_tokens)

        if not overlap:
            return 0.0

        # Fraction of meaningful query terms represented
        # in the document chunk.
        return len(overlap) / len(query_tokens)

    def retrieve(
        self,
        chunks: list[dict],
        query: str,
        file_id: str,
        filename: str,
    ) -> list[EvidenceRecord]:

        query_tokens = self._tokenize(query)

        ranked_chunks: list[tuple[float, dict]] = []

        for chunk in chunks:
            chunk_text = chunk.get("text", "")

            if not chunk_text.strip():
                continue

            chunk_tokens = self._tokenize(chunk_text)

            score = self._score_chunk(
                query_tokens=query_tokens,
                chunk_tokens=chunk_tokens,
            )

            if score >= self.min_score:
                ranked_chunks.append((score, chunk))

        ranked_chunks.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        top_chunks = ranked_chunks[:self.top_k]

        evidence: list[EvidenceRecord] = []

        for index, (score, chunk) in enumerate(top_chunks, start=1):

            evidence.append(
                EvidenceRecord(
                    evidence_id=f"{file_id}_ev_{index:03d}",
                    source_file_id=file_id,
                    source_filename=filename,
                    page_number=chunk.get("page_number"),
                    chunk_id=chunk.get("chunk_id"),
                    text=chunk.get("text", ""),
                    relevance_score=round(score, 4),
                    retrieval_method="keyword_overlap",
                )
            )

        return evidence