from app.rag.engine import RAGEngine
from app.state.evidence import EvidenceRecord


class FakeRetriever:
    def __init__(self, results=None):
        self.results = results or []
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


class FakeSelector:
    def __init__(self, results=None):
        self.results = results or []
        self.calls = []

    def select(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


def test_engine_orchestrates_retriever_and_selector():
    retriever = FakeRetriever(
        [
            {
                "evidence_id": "e1",
                "content": "employee evidence",
                "rerank_score": 0.9,
            }
        ]
    )
    selected = [
        EvidenceRecord(
            evidence_id="e1",
            text="employee evidence",
            relevance_score=0.9,
            retrieval_method="hybrid_rag",
        )
    ]
    selector = FakeSelector(selected)

    engine = RAGEngine(
        retriever=retriever,
        selector=selector,
    )

    result = engine.search(
        query="employee",
        filters={"page_number": 2},
        top_k=3,
        source_file_id="file_1",
    )

    assert result == selected
    assert retriever.calls == [
        {
            "query": "employee",
            "top_k": 3,
            "source_file_id": "file_1",
            "filters": {"page_number": 2},
        }
    ]
    assert selector.calls == [
        {
            "candidates": retriever.results,
            "top_k": 3,
        }
    ]


def test_engine_handles_empty_query():
    retriever = FakeRetriever()
    selector = FakeSelector()
    engine = RAGEngine(retriever=retriever, selector=selector)

    assert engine.search("") == []
    assert retriever.calls == []
    assert selector.calls == []


def test_engine_handles_invalid_top_k():
    retriever = FakeRetriever()
    selector = FakeSelector()
    engine = RAGEngine(retriever=retriever, selector=selector)

    assert engine.search("employee", top_k=0) == []
    assert engine.search("employee", top_k=-1) == []
    assert retriever.calls == []
    assert selector.calls == []


def test_engine_returns_empty_when_retriever_returns_no_candidates():
    retriever = FakeRetriever([])
    selector = FakeSelector([])
    engine = RAGEngine(retriever=retriever, selector=selector)

    assert engine.search("employee") == []
    assert retriever.calls
    assert selector.calls == [
        {
            "candidates": [],
            "top_k": 5,
        }
    ]
