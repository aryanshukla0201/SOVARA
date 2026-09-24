from app.rag.reranker import ScoreReranker


def test_reranker_combines_scores():
    reranker = ScoreReranker()

    candidates = [
        {
            "evidence_id": "a",
            "hybrid_score": 0.8,
            "keyword_score": 0.6,
            "semantic_score": 0.9,
        },
        {
            "evidence_id": "b",
            "hybrid_score": 0.7,
            "keyword_score": 1.0,
            "semantic_score": 0.5,
        },
    ]

    results = reranker.rerank(candidates, top_k=2)

    assert results[0]["evidence_id"] == "a"
    assert results[0]["rerank_score"] == 0.765
    assert results[1]["rerank_score"] == 0.745


def test_reranker_respects_top_k():
    reranker = ScoreReranker()

    candidates = [
        {
            "evidence_id": "a",
            "hybrid_score": 0.9,
        },
        {
            "evidence_id": "b",
            "hybrid_score": 0.8,
        },
        {
            "evidence_id": "c",
            "hybrid_score": 0.7,
        },
    ]

    results = reranker.rerank(candidates, top_k=2)

    assert len(results) == 2
    assert [item["evidence_id"] for item in results] == ["a", "b"]


def test_reranker_is_deterministic_on_ties():
    reranker = ScoreReranker()

    candidates = [
        {
            "evidence_id": "b",
            "hybrid_score": 0.5,
        },
        {
            "evidence_id": "a",
            "hybrid_score": 0.5,
        },
    ]

    results = reranker.rerank(candidates, top_k=2)

    assert [item["evidence_id"] for item in results] == ["a", "b"]


def test_reranker_handles_invalid_requests():
    reranker = ScoreReranker()

    assert reranker.rerank([], top_k=5) == []
    assert reranker.rerank(
        [{"evidence_id": "a", "hybrid_score": 0.5}],
        top_k=0,
    ) == []


def test_reranker_validates_weights():
    try:
        ScoreReranker(
            hybrid_weight=-1.0,
            keyword_weight=0.5,
            semantic_weight=0.5,
        )
        assert False
    except ValueError:
        pass

    try:
        ScoreReranker(
            hybrid_weight=0.0,
            keyword_weight=0.0,
            semantic_weight=0.0,
        )
        assert False
    except ValueError:
        pass
