from app.rag.selector import EvidenceSelector


def test_selector_converts_and_limits_candidates():
    selector = EvidenceSelector()

    candidates = [
        {
            "evidence_id": "e2",
            "content": "second evidence",
            "source_file_id": "file_1",
            "source_filename": "report.pdf",
            "page_number": 2,
            "chunk_id": "chunk_2",
            "rerank_score": 0.8,
        },
        {
            "evidence_id": "e1",
            "content": "first evidence",
            "source_file_id": "file_1",
            "source_filename": "report.pdf",
            "page_number": 1,
            "chunk_id": "chunk_1",
            "rerank_score": 0.9,
        },
    ]

    results = selector.select(candidates, top_k=1)

    assert len(results) == 1
    assert results[0].evidence_id == "e1"
    assert results[0].text == "first evidence"
    assert results[0].source_file_id == "file_1"
    assert results[0].source_filename == "report.pdf"
    assert results[0].page_number == 1
    assert results[0].chunk_id == "chunk_1"
    assert results[0].relevance_score == 0.9
    assert results[0].retrieval_method == "hybrid_rag"


def test_selector_deduplicates_evidence_ids():
    selector = EvidenceSelector()

    candidates = [
        {
            "evidence_id": "e1",
            "content": "older result",
            "rerank_score": 0.7,
        },
        {
            "evidence_id": "e1",
            "content": "better result",
            "rerank_score": 0.9,
        },
        {
            "evidence_id": "e2",
            "content": "other result",
            "rerank_score": 0.8,
        },
    ]

    results = selector.select(candidates, top_k=5)

    assert [item.evidence_id for item in results] == ["e1", "e2"]
    assert results[0].text == "better result"
    assert results[0].relevance_score == 0.9


def test_selector_uses_score_fallbacks():
    selector = EvidenceSelector()

    candidates = [
        {
            "evidence_id": "e1",
            "content": "reranked",
            "rerank_score": 0.9,
            "hybrid_score": 0.7,
            "score": 0.5,
        },
        {
            "evidence_id": "e2",
            "content": "hybrid",
            "hybrid_score": 0.8,
            "score": 0.5,
        },
        {
            "evidence_id": "e3",
            "content": "semantic",
            "score": 0.6,
        },
    ]

    results = selector.select(candidates, top_k=3)

    assert [item.evidence_id for item in results] == ["e1", "e2", "e3"]
    assert results[0].relevance_score == 0.9
    assert results[1].relevance_score == 0.8
    assert results[2].relevance_score == 0.6


def test_selector_skips_invalid_candidates():
    selector = EvidenceSelector()

    candidates = [
        {"content": "missing id", "rerank_score": 1.0},
        {"evidence_id": "", "content": "empty id", "rerank_score": 0.9},
        {
            "evidence_id": "e1",
            "content": "valid",
            "rerank_score": 0.8,
        },
    ]

    results = selector.select(candidates, top_k=5)

    assert [item.evidence_id for item in results] == ["e1"]


def test_selector_handles_invalid_top_k():
    selector = EvidenceSelector()

    candidates = [
        {
            "evidence_id": "e1",
            "content": "valid",
            "rerank_score": 0.8,
        }
    ]

    assert selector.select(candidates, top_k=0) == []
    assert selector.select(candidates, top_k=-1) == []
