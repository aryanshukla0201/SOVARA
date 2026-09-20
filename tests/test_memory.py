from __future__ import annotations

from datetime import timezone

import pytest

from app.memory.manager import MemoryManager
from app.memory.models import MemoryRecord
from app.memory.retrieval import MemoryRetriever
from app.memory.storage import MemoryStorage


def test_memory_record_defaults():
    record = MemoryRecord(
        memory_id="mem_test",
        content="Test memory",
        memory_type="working",
    )

    assert record.metadata == {}
    assert record.source is None
    assert record.reference_id is None
    assert record.created_at.tzinfo == timezone.utc
    assert record.updated_at.tzinfo == timezone.utc


def test_memory_record_rejects_invalid_type():
    with pytest.raises(ValueError):
        MemoryRecord(
            memory_id="mem_test",
            content="Test memory",
            memory_type="invalid",
        )


def test_storage_save_get_delete(tmp_path):
    storage = MemoryStorage(tmp_path / "memory.db")

    record = MemoryRecord(
        memory_id="mem_test",
        content="Persistent memory",
        memory_type="episodic",
        metadata={"source": "test"},
        source="pytest",
        reference_id="ref_001",
    )

    storage.save(record)

    loaded = storage.get("mem_test")

    assert loaded is not None
    assert loaded.memory_id == record.memory_id
    assert loaded.content == record.content
    assert loaded.memory_type == record.memory_type
    assert loaded.metadata == record.metadata
    assert loaded.source == record.source
    assert loaded.reference_id == record.reference_id

    assert storage.delete("mem_test") is True
    assert storage.get("mem_test") is None
    assert storage.delete("mem_test") is False


def test_storage_filters_by_memory_type(tmp_path):
    storage = MemoryStorage(tmp_path / "memory.db")

    storage.save(
        MemoryRecord(
            memory_id="mem_working",
            content="Working memory",
            memory_type="working",
        )
    )
    storage.save(
        MemoryRecord(
            memory_id="mem_semantic",
            content="Semantic memory",
            memory_type="semantic",
        )
    )

    results = storage.list(memory_type="semantic")

    assert len(results) == 1
    assert results[0].memory_id == "mem_semantic"


def test_retriever_orders_by_relevance():
    memories = [
        MemoryRecord(
            memory_id="m1",
            content="Java Spring",
            memory_type="semantic",
        ),
        MemoryRecord(
            memory_id="m2",
            content="Java",
            memory_type="semantic",
        ),
    ]

    results = MemoryRetriever().search(
        memories,
        "Java Spring",
        limit=2,
    )

    assert [record.memory_id for record in results] == ["m1", "m2"]


def test_retriever_respects_limit():
    memories = [
        MemoryRecord(
            memory_id=f"m{i}",
            content="Java Spring Boot",
            memory_type="semantic",
        )
        for i in range(5)
    ]

    results = MemoryRetriever().search(
        memories,
        "Java Spring",
        limit=2,
    )

    assert len(results) == 2


def test_manager_remember_and_recall(tmp_path):
    manager = MemoryManager(
        storage=MemoryStorage(tmp_path / "memory.db"),
    )

    memory = manager.remember(
        "User prefers Java and Spring Boot",
        "semantic",
        {"source": "pytest"},
    )

    results = manager.recall("Java Spring Boot")

    assert len(results) == 1
    assert results[0].memory_id == memory.memory_id
    assert results[0].metadata == {"source": "pytest"}


def test_manager_memory_type_filter(tmp_path):
    manager = MemoryManager(
        storage=MemoryStorage(tmp_path / "memory.db"),
    )

    manager.remember(
        "User is working with Kafka",
        "episodic",
    )
    manager.remember(
        "User prefers Java",
        "semantic",
    )

    results = manager.recall(
        "User",
        memory_type="episodic",
    )

    assert len(results) == 1
    assert results[0].memory_type == "episodic"


def test_manager_rejects_empty_content(tmp_path):
    manager = MemoryManager(
        storage=MemoryStorage(tmp_path / "memory.db"),
    )

    with pytest.raises(ValueError, match="Memory content cannot be empty"):
        manager.remember("   ", "working")


def test_manager_invalid_limit_returns_empty(tmp_path):
    manager = MemoryManager(
        storage=MemoryStorage(tmp_path / "memory.db"),
    )

    manager.remember("Java backend", "semantic")

    assert manager.recall("Java", limit=0) == []
    assert manager.recall("Java", limit=-1) == []
