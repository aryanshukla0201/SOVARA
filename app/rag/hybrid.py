from __future__ import annotations

from typing import Any
from concurrent.futures import ThreadPoolExecutor

from app.rag.query_rewriter import QueryRewriter
from app.rag.reranker import ScoreReranker
from app.rag.score_fusion import HybridScoreFusion
from app.rag.keyword import KeywordRetriever
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


class HybridRetriever:
    def __init__(
        self,
        vector_store,
        keyword_retriever,
        query_rewriter=None,
        reranker=None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        candidate_pool_size: int = 40,
    ):
        if candidate_pool_size <= 0:
            raise ValueError("candidate_pool_size must be positive")

        self.vector_store = vector_store
        self.keyword_retriever = keyword_retriever
        self.query_rewriter = query_rewriter or QueryRewriter()
        self.reranker = reranker or ScoreReranker()
        self.candidate_pool_size = candidate_pool_size
        self.fusion = HybridScoreFusion(
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
        )

    def config_signature(self) -> dict[str, Any]:
        return {
            "semantic_weight": self.fusion.semantic_weight,
            "keyword_weight": self.fusion.keyword_weight,
            "candidate_pool_size": self.candidate_pool_size,
            "query_rewriter": type(self.query_rewriter).__name__,
            "reranker": type(self.reranker).__name__,
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_file_id=None,
        filters=None,
    ):
        if not query or not query.strip() or top_k <= 0:
            return []

        retrieval_queries = self.query_rewriter.rewrite_queries(query)
        if not retrieval_queries:
            return []

        # Original query is always retained. The normalized form is used only
        # as an additional retrieval query when it differs.
        retrieval_query = retrieval_queries[-1]
        pool = max(self.candidate_pool_size, top_k)

        def dense():
            vector = EmbeddingService.embed_text(retrieval_query)
            return self.vector_store.search(
                vector,
                limit=pool,
                source_file_id=source_file_id,
                filters=filters,
            )

        def lexical():
            records = self.vector_store.list_records(
                source_file_id=source_file_id,
                limit=pool,
                filters=filters,
            )
            return self.keyword_retriever.search(
                records,
                retrieval_query,
                top_k=top_k,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            dense_future = executor.submit(dense)
            lexical_future = executor.submit(lexical)
            semantic_results = dense_future.result()
            keyword_results = lexical_future.result()

        merged: dict[str, dict[str, Any]] = {}

        for item in semantic_results:
            evidence_id = str(item.get("evidence_id", "")).strip()
            if not evidence_id:
                continue
            candidate = dict(item)
            candidate["semantic_score"] = float(item.get("score", 0.0))
            candidate["retrieval_method"] = "dense"
            merged[evidence_id] = candidate

        for item in keyword_results:
            evidence_id = str(item.get("evidence_id", "")).strip()
            if not evidence_id:
                continue

            candidate = merged.setdefault(evidence_id, dict(item))
            candidate.update(
                {
                    key: value
                    for key, value in item.items()
                    if key not in {"score", "keyword_score"}
                }
            )
            candidate["keyword_score"] = float(item.get("keyword_score", 0.0))

            if "retrieval_method" in candidate:
                candidate["retrieval_method"] = "hybrid"
            else:
                candidate["retrieval_method"] = "keyword"

        candidates = list(merged.values())
        candidates = self.fusion.fuse(candidates)

        for candidate in candidates:
            candidate["hybrid_score"] = candidate.get(
                "legacy_hybrid_score",
                candidate.get("normalized_hybrid_score", 0.0),
            )

        # Replaceable reranker boundary. Implementations receive the original
        # query plus candidates; deterministic local reranking remains default.
        try:
            reranked = self.reranker.rerank(
                query=query,
                candidates=candidates,
                top_k=top_k,
            )
        except TypeError:
            # Backward compatibility for existing custom P3/P11 rerankers.
            reranked = self.reranker.rerank(candidates, top_k=top_k)

        return reranked[:pool]
