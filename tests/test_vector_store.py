from pathlib import Path

import pytest

from app.services.vector_store import VectorStore


@pytest.fixture
def vector_store(tmp_path: Path):
    VectorStore._client = None

    store = VectorStore(path=str(tmp_path / "qdrant"))

    store.upsert_evidence(
        [
            {
                "evidence_id": "test_001",
                "source_file_id": "file_3d501bed",
                "page_number": 1,
                "content": "test content one",
                "embedding": [0.1] * VectorStore.VECTOR_SIZE,
            },
            {
                "evidence_id": "test_002",
                "source_file_id": "file_c20c028c",
                "page_number": 1,
                "content": "test content two",
                "embedding": [0.2] * VectorStore.VECTOR_SIZE,
            },
            {
                "evidence_id": "test_003",
                "source_file_id": "file_other",
                "page_number": 2,
                "content": "test content three",
                "embedding": [0.3] * VectorStore.VECTOR_SIZE,
            },
        ]
    )

    yield store

    VectorStore._client = None


def test_list_records_returns_payloads(vector_store):
    records = vector_store.list_records(limit=3)

    assert len(records) <= 3
    assert all(isinstance(record, dict) for record in records)

    if records:
        assert "evidence_id" in records[0]
        assert "content" in records[0]


def test_list_records_respects_limit(vector_store):
    records = vector_store.list_records(limit=1)

    assert len(records) <= 1


def test_list_records_filters_by_source_file_id(vector_store):
    records = vector_store.list_records(
        source_file_id="file_3d501bed",
        limit=10,
    )

    assert len(records) == 1
    assert records[0]["source_file_id"] == "file_3d501bed"


def test_list_records_handles_invalid_limit(vector_store):
    assert vector_store.list_records(limit=0) == []
    assert vector_store.list_records(limit=-1) == []


def test_list_records_filters_by_metadata(vector_store):
    records = vector_store.list_records(
        filters={"page_number": 1},
        limit=10,
    )

    assert records
    assert all(
        record.get("page_number") == 1
        for record in records
    )


def test_list_records_filters_by_multiple_metadata_fields(vector_store):
    records = vector_store.list_records(
        filters={
            "source_file_id": "file_c20c028c",
            "page_number": 1,
        },
        limit=10,
    )

    assert len(records) == 1
    assert records[0]["source_file_id"] == "file_c20c028c"
    assert records[0]["page_number"] == 1


def test_list_records_empty_filters_behave_like_no_filter(vector_store):
    records_without_filter = vector_store.list_records(limit=3)
    records_with_empty_filter = vector_store.list_records(
        filters={},
        limit=3,
    )

    assert records_with_empty_filter == records_without_filter


class FakeQueryClient:
    def __init__(self):
        self.query_filter = None

    def query_points(
        self,
        collection_name,
        query,
        query_filter,
        limit,
    ):
        self.query_filter = query_filter

        class Point:
            score = 0.9
            payload = {
                "evidence_id": "test_001",
                "content": "test content",
            }

        class Result:
            points = [Point()]

        return Result()


def test_search_applies_metadata_filters():
    store = object.__new__(VectorStore)
    store.client = FakeQueryClient()

    results = store.search(
        query_vector=[0.1, 0.2],
        limit=5,
        filters={"page_number": 1},
    )

    assert len(results) == 1
    assert results[0]["evidence_id"] == "test_001"

    conditions = store.client.query_filter.must

    assert len(conditions) == 1
    assert conditions[0].key == "page_number"
    assert conditions[0].match.value == 1


def test_search_applies_source_file_id_and_metadata_filters():
    store = object.__new__(VectorStore)
    store.client = FakeQueryClient()

    store.search(
        query_vector=[0.1, 0.2],
        limit=5,
        source_file_id="file_123",
        filters={"page_number": 1},
    )

    conditions = store.client.query_filter.must

    assert len(conditions) == 2
    assert conditions[0].key == "source_file_id"
    assert conditions[0].match.value == "file_123"
    assert conditions[1].key == "page_number"
    assert conditions[1].match.value == 1
