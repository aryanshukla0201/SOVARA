from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.state.manager import AgentStateManager
from app.state.store import DurableStateStore


def make_manager(tmp_path: Path) -> AgentStateManager:
    return AgentStateManager(
        DurableStateStore(tmp_path / "state.db")
    )


def test_stale_writer_is_rejected(tmp_path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Concurrent task")

    writer_a = manager.get_task("task-1")
    writer_b = manager.get_task("task-1")

    writer_a.metadata["writer"] = "A"
    writer_a.touch()

    saved = manager.store.save(
        writer_a,
        expected_version=0,
    )

    assert saved.version == 1

    writer_b.metadata["writer"] = "B"
    writer_b.touch()

    with pytest.raises(
        ValueError,
        match="State version conflict",
    ):
        manager.store.save(
            writer_b,
            expected_version=0,
        )

    final = manager.get_task("task-1")

    assert final.metadata["writer"] == "A"
    assert final.version == 1


def test_concurrent_writers_do_not_corrupt_state(tmp_path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Concurrent updates")

    def write_update(index: int):
        local_manager = make_manager(tmp_path)
        state = local_manager.get_task("task-1")

        state.metadata[f"writer_{index}"] = index
        state.touch()

        try:
            return local_manager.store.save(
                state,
                expected_version=state.version - 1,
            )
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(write_update, range(8))
        )

    successful = [
        result
        for result in results
        if result is not None
    ]

    final = manager.get_task("task-1")

    assert len(successful) >= 1
    assert final.version == len(successful)

    assert final.task_id == "task-1"
    assert final.goal == "Concurrent updates"

    for key, value in final.metadata.items():
        assert key.startswith("writer_")
        assert isinstance(value, int)


def test_checkpoint_duplicate_is_atomic(tmp_path):
    manager = make_manager(tmp_path)

    task = manager.create_task(
        "task-1",
        "Checkpoint atomicity",
    )

    first = manager.checkpoint(
        task.task_id,
        "checkpoint-1",
    )

    assert first.checkpoint_id == "checkpoint-1"

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        manager.checkpoint(
            task.task_id,
            "checkpoint-1",
        )

    stored = manager.get_checkpoint(
        task.task_id,
        "checkpoint-1",
    )

    assert stored is not None
    assert stored.checkpoint_id == "checkpoint-1"


def test_checkpoint_history_remains_ordered_after_restart(tmp_path):
    manager1 = make_manager(tmp_path)

    task = manager1.create_task(
        "task-1",
        "Checkpoint ordering",
    )

    manager1.checkpoint(
        task.task_id,
        "checkpoint-1",
    )

    manager1.add_step(
        task.task_id,
        "step-1",
    )

    manager1.checkpoint(
        task.task_id,
        "checkpoint-2",
    )

    manager2 = make_manager(tmp_path)

    checkpoints = manager2.list_checkpoints(
        task.task_id,
    )

    assert [
        checkpoint.checkpoint_id
        for checkpoint in checkpoints
    ] == [
        "checkpoint-1",
        "checkpoint-2",
    ]

    assert checkpoints[0].version < checkpoints[1].version
