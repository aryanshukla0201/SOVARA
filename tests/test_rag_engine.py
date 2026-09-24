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


def test_rag_retrieval_budget_is_consumed_only_on_cache_miss():
    from app.governance.budget import ResourceBudget, ResourceBudgetGovernor
    from app.rag.engine import RAGEngine

    class Retriever:
        def __init__(self):
            self.calls = 0

        def search(self, **kwargs):
            self.calls += 1
            return []

    retriever = Retriever()
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_retrieval_calls=1)
    )
    engine = RAGEngine(
        retriever=retriever,
        budget_governor=governor,
    )

    engine.search("hello")
    engine.search("hello")

    assert retriever.calls == 1
    assert governor.snapshot()["usage"]["retrieval_calls"] == 1


def test_rag_retrieval_budget_blocks_cache_miss():
    from app.governance.budget import BudgetExceededError, ResourceBudget, ResourceBudgetGovernor
    from app.rag.engine import RAGEngine

    class Retriever:
        def __init__(self):
            self.calls = 0

        def search(self, **kwargs):
            self.calls += 1
            return []

    retriever = Retriever()
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_retrieval_calls=0)
    )
    engine = RAGEngine(
        retriever=retriever,
        budget_governor=governor,
    )

    try:
        engine.search("hello")
        assert False, "Expected retrieval budget to be exceeded"
    except BudgetExceededError as exc:
        assert exc.resource == "retrieval_calls"

    assert retriever.calls == 0


def test_rag_context_budget_limits_compression():
    from app.governance.budget import ResourceBudget, ResourceBudgetGovernor
    from app.rag.engine import RAGEngine
    from app.state.evidence import EvidenceRecord

    class Retriever:
        def search(self, **kwargs):
            return [
                {
                    "evidence_id": "e1",
                    "source": "test",
                    "text": "abcdefghijklmnopqrstuvwxyz",
                }
            ]

    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_retrieval_calls=1,
            max_context_tokens=3,
        )
    )

    engine = RAGEngine(
        retriever=Retriever(),
        budget_governor=governor,
    )

    results = engine.search("hello")

    assert len(results) == 1
    assert governor.snapshot()["usage"]["context_tokens"] <= 3
    assert len(results[0].text) <= 12


def test_rag_context_budget_is_cumulative():
    from app.governance.budget import BudgetExceededError, ResourceBudget, ResourceBudgetGovernor
    from app.rag.engine import RAGEngine
    from app.state.evidence import EvidenceRecord

    class Retriever:
        def search(self, **kwargs):
            return [
                {
                    "evidence_id": kwargs["query"],
                    "source": "test",
                    "text": "12345678",
                }
            ]

    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_retrieval_calls=2,
            max_context_tokens=2,
        )
    )

    engine = RAGEngine(
        retriever=Retriever(),
        budget_governor=governor,
    )

    engine.search("first")

    try:
        engine.search("second")
        assert False, "Expected cumulative context budget to be exceeded"
    except BudgetExceededError as exc:
        assert exc.resource == "context_tokens"

    snapshot = governor.snapshot()
    assert snapshot["usage"]["context_tokens"] == 2
    assert snapshot["usage"]["retrieval_calls"] == 1


def test_rag_retrieval_budget_is_released_when_retriever_fails():
    from app.governance.budget import ResourceBudget, ResourceBudgetGovernor
    from app.rag.engine import RAGEngine

    class Retriever:
        def search(self, **kwargs):
            raise RuntimeError("retrieval failed")

    governor = ResourceBudgetGovernor(
        ResourceBudget(max_retrieval_calls=1)
    )

    engine = RAGEngine(
        retriever=Retriever(),
        budget_governor=governor,
    )

    try:
        engine.search("hello")
        assert False, "Expected retrieval failure"
    except RuntimeError:
        pass

    assert governor.snapshot()["usage"]["retrieval_calls"] == 0
