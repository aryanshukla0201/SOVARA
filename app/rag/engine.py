from __future__ import annotations

from typing import Any

from app.state.evidence import EvidenceRecord
from app.rag.citations import CitationBuilder
from app.rag.compression import ContextCompressor
from app.rag.diversity import EvidenceDiversity
from app.services.ttl_cache import TTLCache
from app.governance.budget import ResourceBudgetGovernor


class RAGEngine:
    def __init__(
        self,
        retriever=None,
        selector=None,
        cache_size: int = 256,
        cache_ttl_seconds: int = 300,
        diversity=None,
        compressor=None,
        max_context_tokens: int | None = None,
        budget_governor: ResourceBudgetGovernor | None = None,
    ):
        from app.rag.hybrid import HybridRetriever

        self.retriever = retriever or HybridRetriever()
        self.selector = selector
        if self.selector is None:
            from app.rag.selector import EvidenceSelector
            self.selector = EvidenceSelector()

        self.diversity = diversity or EvidenceDiversity()
        self.compressor = compressor or ContextCompressor()
        self.max_context_tokens = max_context_tokens
        self.budget_governor = budget_governor
        self.cache = TTLCache[list[EvidenceRecord]](
            max_size=cache_size,
            ttl_seconds=cache_ttl_seconds,
        )

    def _retrieval_config(self) -> dict[str, Any]:
        config = {}
        if hasattr(self.retriever, "config_signature"):
            config = dict(self.retriever.config_signature())
        config["max_context_tokens"] = self.max_context_tokens
        config["diversity"] = type(self.diversity).__name__
        config["compressor"] = type(self.compressor).__name__
        return config

    def _cache_key(
        self,
        query: str,
        filters: dict[str, Any] | None,
        top_k: int,
        source_file_id: str | None,
    ) -> str:
        import hashlib
        import json

        payload = {
            "query": query,
            "filters": filters or {},
            "top_k": top_k,
            "source_file_id": source_file_id,
            "retrieval_config": self._retrieval_config(),
        }

        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_file_id: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[EvidenceRecord]:
        if not query or not query.strip() or top_k <= 0:
            return []

        cache_key = self._cache_key(
            query=query,
            filters=filters,
            top_k=top_k,
            source_file_id=source_file_id,
        )

        cached = self.cache.get(cache_key)

        if cached is None:
            if self.budget_governor is not None:
                # Context budget is checked before retrieval so an already
                # exhausted run does not perform unnecessary retrieval work.
                context_remaining = self.budget_governor.remaining(
                    "context_tokens"
                )
                if (
                    context_remaining is not None
                    and context_remaining <= 0
                ):
                    from app.governance.budget import BudgetExceededError

                    raise BudgetExceededError(
                        "context_tokens",
                        self.budget_governor.budget.max_context_tokens,
                        self.budget_governor.usage.context_tokens,
                        1,
                    )

                self.budget_governor.reserve_retrieval_call()

            try:
                candidates = self.retriever.search(
                    query=query,
                    top_k=top_k,
                    source_file_id=source_file_id,
                    filters=filters,
                )
            except Exception:
                if self.budget_governor is not None:
                    self.budget_governor.release("retrieval_calls")
                raise

            candidates = self.diversity.select(
                candidates,
                max(top_k, len(candidates)),
            )
            selected = self.selector.select(
                candidates=candidates,
                top_k=top_k,
            )

            context_limit = self.max_context_tokens

            if self.budget_governor is not None:
                remaining = self.budget_governor.remaining(
                    "context_tokens"
                )

                if remaining is not None:
                    if context_limit is None:
                        context_limit = remaining
                    else:
                        context_limit = min(
                            context_limit,
                            remaining,
                        )

            selected = self.compressor.compress(
                selected,
                max_context_tokens=context_limit,
            )

            # Charge the actual compressed context, not the configured
            # compression ceiling.
            if self.budget_governor is not None:
                context_tokens = sum(
                    self.compressor.count_tokens(
                        getattr(item, "text", None)
                        if getattr(item, "text", None) is not None
                        else (
                            item.get("content", "")
                            if isinstance(item, dict)
                            else ""
                        )
                    )
                    for item in selected
                )

                if context_tokens:
                    self.budget_governor.reserve_context_tokens(
                        context_tokens
                    )

            # Force deterministic citation construction so the source-to-evidence
            # trace is available to P12 without inventing missing metadata.
            CitationBuilder.build(selected)

            self.cache.set(cache_key, selected)
            return selected

        # Cached retrieval does not consume a retrieval-call budget.
        if self.budget_governor is not None:
            context_tokens = sum(
                self.compressor.count_tokens(
                    getattr(item, "text", None)
                    if getattr(item, "text", None) is not None
                    else (
                        item.get("content", "")
                        if isinstance(item, dict)
                        else ""
                    )
                )
                for item in cached
            )

            if context_tokens:
                self.budget_governor.reserve_context_tokens(
                    context_tokens
                )

        return cached
