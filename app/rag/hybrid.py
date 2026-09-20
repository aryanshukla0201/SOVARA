from __future__ import annotations
from typing import Any
from app.rag.keyword import KeywordRetriever
from app.rag.query_rewriter import QueryRewriter
from app.rag.reranker import ScoreReranker
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
class HybridRetriever:
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        keyword_retriever: KeywordRetriever | None = None,
        query_rewriter: QueryRewriter | None = None,
        reranker: ScoreReranker | None = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        if semantic_weight < 0:
            raise ValueError("semantic_weight must be non-negative")
        if keyword_weight < 0:
            raise ValueError("keyword_weight must be non-negative")
        if semantic_weight + keyword_weight <= 0:
            raise ValueError(
                "at least one retrieval weight must be positive"
            )
        self.vector_store = vector_store or VectorStore()
        self.keyword_retriever = (
            keyword_retriever or KeywordRetriever()
        )
        self.query_rewriter = (
            query_rewriter or QueryRewriter()
        )
        self.reranker = reranker or ScoreReranker()
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
    def search(
        self,
        query: str,
        top_k: int = 5,
        source_file_id: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        rewritten_query = self.query_rewriter.rewrite(query)
        if not rewritten_query or top_k <= 0:
            return []
        candidate_limit = top_k * 2
        query_vector = EmbeddingService.embed_text(
            rewritten_query
        )
        if not query_vector:
            return []
        semantic_results = self.vector_store.search(
            query_vector=query_vector,
            limit=candidate_limit,
            source_file_id=source_file_id,
            filters=filters,
        )
        records = self.vector_store.list_records(
            source_file_id=source_file_id,
            filters=filters,
            limit=max(candidate_limit, 1000),
        )
        keyword_results = self.keyword_retriever.search(
            records=records,
            query=rewritten_query,
            top_k=candidate_limit,
        )
        candidates: dict[str, dict[str, Any]] = {}
        for item in semantic_results:
            evidence_id = item.get("evidence_id")
            if not evidence_id:
                continue
            candidates[str(evidence_id)] = {
                **item,
                "semantic_score": float(
                    item.get("score", 0.0)
                ),
                "keyword_score": 0.0,
            }
        for item in keyword_results:
            evidence_id = item.get("evidence_id")
            if not evidence_id:
                continue
            key = str(evidence_id)
            if key not in candidates:
                candidates[key] = dict(item)
            candidates[key]["keyword_score"] = float(
                item.get("keyword_score", 0.0)
            )
        results = []
        total_weight = (
            self.semantic_weight + self.keyword_weight
        )
        for item in candidates.values():
            semantic_score = float(
                item.get("semantic_score", 0.0)
            )
            keyword_score = float(
                item.get("keyword_score", 0.0)
            )
            hybrid_score = (
                (
                    self.semantic_weight * semantic_score
                    + self.keyword_weight * keyword_score
                )
                / total_weight
            )
            result = dict(item)
            result["hybrid_score"] = round(
                hybrid_score,
                4,
            )
            results.append(result)
        results.sort(
            key=lambda item: (
                -float(item["hybrid_score"]),
                str(item.get("evidence_id", "")),
            )
        )
        return self.reranker.rerank(
            results,
            top_k=top_k,
        )
