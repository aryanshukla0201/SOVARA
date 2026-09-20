from app.rag.keyword import KeywordRetriever


def test_keyword_retrieval_scores_query_term_coverage():
    retriever = KeywordRetriever()

    records = [
        {"evidence_id": "a", "content": "The engine uses a spark plug for ignition."},
        {"evidence_id": "b", "content": "The engine has an exhaust valve."},
        {"evidence_id": "c", "content": "Completely unrelated text."},
    ]

    results = retriever.search(records, "engine spark plug", top_k=3)

    assert [item["evidence_id"] for item in results] == ["a", "b"]
    assert results[0]["keyword_score"] == 1.0
    assert results[1]["keyword_score"] == 0.3333


def test_keyword_retrieval_is_case_insensitive():
    retriever = KeywordRetriever()

    records = [
        {"evidence_id": "a", "content": "Spark Plug ENGINE"},
    ]

    results = retriever.search(records, "engine spark plug")

    assert len(results) == 1
    assert results[0]["keyword_score"] == 1.0


def test_keyword_retrieval_ignores_empty_content():
    retriever = KeywordRetriever()

    records = [
        {"evidence_id": "a", "content": ""},
        {"evidence_id": "b", "content": "engine"},
    ]

    results = retriever.search(records, "engine")

    assert [item["evidence_id"] for item in results] == ["b"]


def test_keyword_retrieval_handles_invalid_requests():
    retriever = KeywordRetriever()

    records = [
        {"evidence_id": "a", "content": "engine"},
    ]

    assert retriever.search(records, "", top_k=5) == []
    assert retriever.search(records, "engine", top_k=0) == []


def test_keyword_retrieval_tie_breaks_by_evidence_id():
    retriever = KeywordRetriever()

    records = [
        {"evidence_id": "b", "content": "engine"},
        {"evidence_id": "a", "content": "engine"},
    ]

    results = retriever.search(records, "engine")

    assert [item["evidence_id"] for item in results] == ["a", "b"]
