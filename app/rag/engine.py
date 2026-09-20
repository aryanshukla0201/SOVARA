from __future__ import annotations

from typing import Any

from app.rag.hybrid import HybridRetriever
from app.rag.selector import EvidenceSelector
from app.state.evidence import EvidenceRecord


class RAGEngine:
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        selector: EvidenceSelector | None = None,
    ):
        self.retriever = retriever or HybridRetriever()
        self.selector = selector or EvidenceSelector()

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        source_file_id: str | None = None,
    ) -> list[EvidenceRecord]:
        if not query or not query.strip() or top_k <= 0:
            return []

        candidates = self.retriever.search(
            query=query,
            top_k=top_k,
            source_file_id=source_file_id,
            filters=filters,
        )

        return self.selector.select(
            candidates=candidates,
            top_k=top_k,
        )
