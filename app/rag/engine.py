from __future__ import annotations

import hashlib
import json
from typing import Any

from app.rag.hybrid import HybridRetriever
from app.rag.selector import EvidenceSelector
from app.services.ttl_cache import TTLCache
from app.state.evidence import EvidenceRecord


class RAGEngine:
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        selector: EvidenceSelector | None = None,
        *,
        cache_size: int = 256,
        cache_ttl_seconds: float = 300.0,
    ):
        self.retriever = retriever or HybridRetriever()
        self.selector = selector or EvidenceSelector()
        self._cache = TTLCache[list[EvidenceRecord]](
            max_size=cache_size,
            ttl_seconds=cache_ttl_seconds,
        )

    @staticmethod
    def _cache_key(
        query: str,
        filters: dict[str, Any] | None,
        top_k: int,
        source_file_id: str | None,
    ) -> str:
        payload = {
            "query": query.strip(),
            "filters": filters or {},
            "top_k": top_k,
            "source_file_id": source_file_id,
        }

        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        source_file_id: str | None = None,
    ) -> list[EvidenceRecord]:
        if not query or not query.strip() or top_k <= 0:
            return []

        cache_key = self._cache_key(
            query=query,
            filters=filters,
            top_k=top_k,
            source_file_id=source_file_id,
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            return list(cached)

        candidates = self.retriever.search(
            query=query,
            top_k=top_k,
            source_file_id=source_file_id,
            filters=filters,
        )

        results = self.selector.select(
            candidates=candidates,
            top_k=top_k,
        )

        self._cache.set(cache_key, list(results))

        return results
