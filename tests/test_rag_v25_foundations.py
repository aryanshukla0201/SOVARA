from app.rag.query_rewriter import QueryRewriter
from app.rag.score_fusion import ScoreNormalizer, HybridScoreFusion


def test_query_rewriter_preserves_original_query():
    rewriter = QueryRewriter()
    query = "What  is   SOVARA?"
    queries = rewriter.rewrite_queries(query)
    assert queries[0] == query
    assert rewriter.rewrite(query) == "what is sovara?"


def test_score_normalizer_is_deterministic():
    assert ScoreNormalizer.normalize([1.0, 2.0, 3.0]) == [0.0, 0.5, 1.0]
    assert ScoreNormalizer.normalize([0.5, 0.5]) == [0.5, 0.5]


def test_hybrid_fusion_normalizes_signals():
    fusion = HybridScoreFusion(semantic_weight=0.7, keyword_weight=0.3)
    candidates = [
        {"evidence_id": "a", "semantic_score": 0.5, "keyword_score": 0.2},
        {"evidence_id": "b", "semantic_score": 1.0, "keyword_score": 0.8},
    ]
    result = fusion.fuse(candidates)
    assert result[0]["evidence_id"] == "b"
    assert result[0]["semantic_score_normalized"] == 1.0
    assert result[0]["keyword_score_normalized"] == 1.0
    assert result[0]["hybrid_score"] == 1.0
