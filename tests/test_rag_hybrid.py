from app.rag.hybrid import HybridRetriever


class FakeVectorStore:
    def search(self, query_vector, limit, source_file_id=None, filters=None):
        return [
            {
                "evidence_id": "semantic_only",
                "content": "semantic result",
                "score": 0.9,
            },
            {
                "evidence_id": "both",
                "content": "shared result",
                "score": 0.8,
            },
        ]

    def list_records(self, source_file_id=None, limit=1000, filters=None):
        return [
            {
                "evidence_id": "both",
                "content": "shared result",
            },
            {
                "evidence_id": "keyword_only",
                "content": "keyword result",
            },
        ]


class FakeKeywordRetriever:
    def search(self, records, query, top_k):
        return [
            {
                "evidence_id": "both",
                "content": "shared result",
                "keyword_score": 1.0,
            },
            {
                "evidence_id": "keyword_only",
                "content": "keyword result",
                "keyword_score": 0.8,
            },
        ]


def test_hybrid_retriever_merges_candidates(monkeypatch):
    monkeypatch.setattr(
        "app.rag.hybrid.EmbeddingService.embed_text",
        lambda query: [0.1, 0.2],
    )

    retriever = HybridRetriever(
        vector_store=FakeVectorStore(),
        keyword_retriever=FakeKeywordRetriever(),
    )

    results = retriever.search("engine", top_k=3)

    assert [item["evidence_id"] for item in results] == [
        "both",
        "semantic_only",
        "keyword_only",
    ]


def test_hybrid_retriever_calculates_combined_score(monkeypatch):
    monkeypatch.setattr(
        "app.rag.hybrid.EmbeddingService.embed_text",
        lambda query: [0.1, 0.2],
    )

    retriever = HybridRetriever(
        vector_store=FakeVectorStore(),
        keyword_retriever=FakeKeywordRetriever(),
        semantic_weight=0.7,
        keyword_weight=0.3,
    )

    results = retriever.search("engine", top_k=3)

    both = next(
        item
        for item in results
        if item["evidence_id"] == "both"
    )

    assert both["semantic_score"] == 0.8
    assert both["keyword_score"] == 1.0
    assert both["hybrid_score"] == 0.86


def test_hybrid_retriever_preserves_scores_for_single_source(monkeypatch):
    monkeypatch.setattr(
        "app.rag.hybrid.EmbeddingService.embed_text",
        lambda query: [0.1, 0.2],
    )

    retriever = HybridRetriever(
        vector_store=FakeVectorStore(),
        keyword_retriever=FakeKeywordRetriever(),
    )

    results = retriever.search("engine", top_k=3)

    semantic_only = next(
        item
        for item in results
        if item["evidence_id"] == "semantic_only"
    )

    keyword_only = next(
        item
        for item in results
        if item["evidence_id"] == "keyword_only"
    )

    assert semantic_only["semantic_score"] == 0.9
    assert semantic_only["keyword_score"] == 0.0

    assert keyword_only.get("semantic_score", 0.0) == 0.0
    assert keyword_only["keyword_score"] == 0.8


def test_hybrid_retriever_handles_invalid_requests():
    retriever = HybridRetriever(
        vector_store=FakeVectorStore(),
        keyword_retriever=FakeKeywordRetriever(),
    )

    assert retriever.search("", top_k=5) == []
    assert retriever.search("engine", top_k=0) == []


def test_hybrid_retriever_validates_weights():
    try:
        HybridRetriever(
            vector_store=FakeVectorStore(),
            keyword_retriever=FakeKeywordRetriever(),
            semantic_weight=0.0,
            keyword_weight=0.0,
        )
        assert False
    except ValueError:
        pass

class FakeReranker:
    def __init__(self):
        self.candidates = None
        self.top_k = None

    def rerank(self, candidates, top_k):
        self.candidates = candidates
        self.top_k = top_k
        return candidates[:top_k]


def test_hybrid_retriever_uses_reranker(monkeypatch):
    monkeypatch.setattr(
        "app.rag.hybrid.EmbeddingService.embed_text",
        lambda query: [0.1, 0.2],
    )

    reranker = FakeReranker()

    retriever = HybridRetriever(
        vector_store=FakeVectorStore(),
        keyword_retriever=FakeKeywordRetriever(),
        reranker=reranker,
    )

    results = retriever.search("engine", top_k=2)

    assert reranker.candidates is not None
    assert len(reranker.candidates) == 3
    assert reranker.top_k == 2
    assert len(results) == 2


def test_hybrid_retriever_propagates_filters(monkeypatch):
    monkeypatch.setattr(
        "app.rag.hybrid.EmbeddingService.embed_text",
        lambda query: [0.1, 0.2],
    )

    class FilterAwareVectorStore(FakeVectorStore):
        def __init__(self):
            self.search_filters = None
            self.list_filters = None

        def search(self, query_vector, limit, source_file_id=None, filters=None):
            self.search_filters = filters
            return super().search(query_vector, limit, source_file_id)

        def list_records(self, source_file_id=None, limit=1000, filters=None):
            self.list_filters = filters
            return super().list_records(source_file_id, limit)

    vector_store = FilterAwareVectorStore()

    retriever = HybridRetriever(
        vector_store=vector_store,
        keyword_retriever=FakeKeywordRetriever(),
    )

    filters = {
        "page_number": 2,
        "source_filename": "report.pdf",
    }

    retriever.search(
        "engine",
        top_k=3,
        filters=filters,
    )

    assert vector_store.search_filters == filters
    assert vector_store.list_filters == filters
