from __future__ import annotations

from datetime import datetime, timezone

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


def test_storage_round_trips_timestamps(tmp_path):
    storage = MemoryStorage(tmp_path / "memory.db")

    created_at = datetime(
        2026,
        9,
        20,
        12,
        30,
        45,
        123456,
        tzinfo=timezone.utc,
    )
    updated_at = datetime(
        2026,
        9,
        20,
        13,
        45,
        55,
        654321,
        tzinfo=timezone.utc,
    )

    record = MemoryRecord(
        memory_id="mem_timestamp",
        content="Timestamp test",
        memory_type="episodic",
        created_at=created_at,
        updated_at=updated_at,
    )

    storage.save(record)

    loaded = storage.get(record.memory_id)

    assert loaded is not None
    assert loaded.created_at == created_at
    assert loaded.updated_at == updated_at
    assert loaded.created_at.tzinfo == timezone.utc
    assert loaded.updated_at.tzinfo == timezone.utc


def test_storage_persists_across_instances(tmp_path):
    db_path = tmp_path / "memory.db"

    first_storage = MemoryStorage(db_path)
    record = MemoryRecord(
        memory_id="mem_restart",
        content="Survives storage recreation",
        memory_type="semantic",
        metadata={"test": "restart"},
    )

    first_storage.save(record)

    second_storage = MemoryStorage(db_path)
    loaded = second_storage.get(record.memory_id)

    assert loaded is not None
    assert loaded.memory_id == record.memory_id
    assert loaded.content == record.content
    assert loaded.memory_type == record.memory_type
    assert loaded.metadata == record.metadata
    assert loaded.created_at == record.created_at
    assert loaded.updated_at == record.updated_at


def test_storage_handles_special_characters_and_sql_like_content(tmp_path):
    storage = MemoryStorage(tmp_path / "memory.db")

    content = (
        "Robert'); DROP TABLE memory_records; -- "
        "O'Reilly %_ [] 日本語 🚀"
    )

    record = MemoryRecord(
        memory_id="mem_special",
        content=content,
        memory_type="semantic",
        metadata={
            "note": "quotes: ' \" ; --",
            "symbols": "%_[]",
        },
    )

    storage.save(record)

    loaded = storage.get(record.memory_id)

    assert loaded is not None
    assert loaded.content == content
    assert loaded.metadata == record.metadata

    assert storage.get(record.memory_id) is not None


def test_storage_allows_duplicate_content_with_unique_ids(tmp_path):
    storage = MemoryStorage(tmp_path / "memory.db")

    first = MemoryRecord(
        memory_id="mem_duplicate_1",
        content="Same memory content",
        memory_type="semantic",
    )
    second = MemoryRecord(
        memory_id="mem_duplicate_2",
        content="Same memory content",
        memory_type="semantic",
    )

    storage.save(first)
    storage.save(second)

    first_loaded = storage.get(first.memory_id)
    second_loaded = storage.get(second.memory_id)

    assert first_loaded is not None
    assert second_loaded is not None
    assert first_loaded.content == second_loaded.content
    assert first_loaded.memory_id != second_loaded.memory_id

    results = storage.list()
    assert {record.memory_id for record in results} == {
        first.memory_id,
        second.memory_id,
    }


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


def test_retriever_returns_empty_for_no_match():
    memories = [
        MemoryRecord(
            memory_id="m1",
            content="Java Spring",
            memory_type="semantic",
        ),
    ]

    assert MemoryRetriever().search(
        memories,
        "Python Kafka",
        limit=5,
    ) == []


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


def test_manager_round_trip_persists_memory(tmp_path):
    db_path = tmp_path / "memory.db"

    first_manager = MemoryManager(
        storage=MemoryStorage(db_path),
    )

    memory = first_manager.remember(
        "User works with Kafka and Java",
        "semantic",
        {"source": "pytest"},
    )

    second_manager = MemoryManager(
        storage=MemoryStorage(db_path),
    )

    results = second_manager.recall("Kafka Java")

    assert len(results) == 1
    assert results[0].memory_id == memory.memory_id
    assert results[0].content == memory.content
    assert results[0].metadata == memory.metadata
    assert results[0].created_at == memory.created_at
    assert results[0].updated_at == memory.updated_at


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


def test_manager_recall_returns_empty_when_nothing_matches(tmp_path):
    manager = MemoryManager(
        storage=MemoryStorage(tmp_path / "memory.db"),
    )

    manager.remember("Java backend development", "semantic")

    assert manager.recall("Quantum physics") == []


def test_storage_concurrent_reads_and_writes(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    db_path = tmp_path / "memory.db"
    storage = MemoryStorage(db_path)

    for index in range(10):
        storage.save(
            MemoryRecord(
                memory_id=f"mem_initial_{index}",
                content=f"Initial memory {index}",
                memory_type="working",
            )
        )

    def write_memory(index: int) -> str:
        writer = MemoryStorage(db_path)
        record = MemoryRecord(
            memory_id=f"mem_concurrent_{index}",
            content=f"Concurrent memory {index}",
            memory_type="working",
        )
        writer.save(record)
        return record.memory_id

    def read_memories(_: int) -> int:
        reader = MemoryStorage(db_path)
        return len(reader.list())

    with ThreadPoolExecutor(max_workers=8) as executor:
        write_ids = list(executor.map(write_memory, range(20)))
        read_counts = list(executor.map(read_memories, range(20)))

    assert len(write_ids) == 20
    assert len(read_counts) == 20
    assert all(count >= 10 for count in read_counts)

    final_storage = MemoryStorage(db_path)
    records = final_storage.list()

    assert len(records) == 30
    assert {record.memory_id for record in records} >= set(write_ids)


def test_storage_concurrent_read_write(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    db_path = tmp_path / "memory.db"
    storage = MemoryStorage(db_path)

    for index in range(10):
        storage.save(
            MemoryRecord(
                memory_id=f"mem_rw_initial_{index}",
                content=f"Read write initial {index}",
                memory_type="working",
            )
        )

    def write_memory(index: int) -> str:
        writer = MemoryStorage(db_path)
        record = MemoryRecord(
            memory_id=f"mem_rw_{index}",
            content=f"Read write concurrent {index}",
            memory_type="working",
        )
        writer.save(record)
        return record.memory_id

    def read_memory(_: int) -> int:
        reader = MemoryStorage(db_path)
        return len(reader.list())

    with ThreadPoolExecutor(max_workers=8) as executor:
        write_futures = [
            executor.submit(write_memory, index)
            for index in range(20)
        ]
        read_futures = [
            executor.submit(read_memory, index)
            for index in range(20)
        ]

        write_ids = [future.result() for future in write_futures]
        read_counts = [future.result() for future in read_futures]

    assert len(write_ids) == 20
    assert len(read_counts) == 20
    assert all(count >= 10 for count in read_counts)

    final_storage = MemoryStorage(db_path)
    records = final_storage.list()

    assert len(records) == 30
    assert {record.memory_id for record in records} >= set(write_ids)


def test_storage_persists_across_processes(tmp_path):
    import subprocess
    import sys

    db_path = tmp_path / "memory.db"

    write_code = """
from app.memory.models import MemoryRecord
from app.memory.storage import MemoryStorage
import sys

storage = MemoryStorage(sys.argv[1])
record = MemoryRecord(
    memory_id="mem_process",
    content="Memory persisted across process boundary",
    memory_type="episodic",
    metadata={"source": "process-a"},
)
storage.save(record)
"""

    read_code = """
from app.memory.storage import MemoryStorage
import sys

storage = MemoryStorage(sys.argv[1])
record = storage.get("mem_process")

assert record is not None
assert record.content == "Memory persisted across process boundary"
assert record.memory_type == "episodic"
assert record.metadata == {"source": "process-a"}
"""

    python_executable = sys.executable

    write_result = subprocess.run(
        [python_executable, "-c", write_code, str(db_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert write_result.returncode == 0, write_result.stderr

    read_result = subprocess.run(
        [python_executable, "-c", read_code, str(db_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert read_result.returncode == 0, read_result.stderr
