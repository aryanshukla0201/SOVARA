from app.rag.engine import RAGEngine


class FakeRetriever:
    def __init__(self):
        self.calls = 0

    def search(self, **kwargs):
        self.calls += 1
        return [
            {
                "evidence_id": "ev-1",
                "source_file_id": kwargs.get("source_file_id"),
                "content": "cached evidence",
                "rerank_score": 0.9,
            }
        ]


def test_rag_engine_caches_identical_search():
    retriever = FakeRetriever()
    engine = RAGEngine(retriever=retriever)

    first = engine.search("What is SOVARA?", top_k=5)
    second = engine.search("What is SOVARA?", top_k=5)

    assert retriever.calls == 1
    assert first == second


def test_rag_engine_cache_key_includes_request_parameters():
    retriever = FakeRetriever()
    engine = RAGEngine(retriever=retriever)

    engine.search("same query", top_k=5)
    engine.search("same query", top_k=10)
    engine.search("same query", top_k=5, source_file_id="file-1")
    engine.search("same query", top_k=5, filters={"type": "pdf"})

    assert retriever.calls == 4


def test_rag_engine_does_not_cache_invalid_requests():
    retriever = FakeRetriever()
    engine = RAGEngine(retriever=retriever)

    assert engine.search("") == []
    assert engine.search("   ") == []
    assert engine.search("query", top_k=0) == []

    assert retriever.calls == 0
