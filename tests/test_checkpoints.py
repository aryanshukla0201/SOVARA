from pathlib import Path

import pytest

from app.state.manager import AgentStateManager
from app.state.store import DurableStateStore


def make_manager(tmp_path: Path) -> AgentStateManager:
    database = tmp_path / "state.db"

    return AgentStateManager(
        store=DurableStateStore(database),
    )


def test_checkpoint_is_persisted(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task(
        "task-1",
        "Analyze equipment",
    )

    checkpoint = manager.checkpoint(
        "task-1",
        "cp-1",
    )

    restored = manager.get_checkpoint(
        "task-1",
        "cp-1",
    )

    assert restored is not None
    assert restored.checkpoint_id == checkpoint.checkpoint_id
    assert restored.state.task_id == "task-1"


def test_duplicate_checkpoint_is_rejected(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task(
        "task-1",
        "Analyze equipment",
    )

    manager.checkpoint(
        "task-1",
        "cp-1",
    )

    with pytest.raises(
        ValueError,
        match="Checkpoint already exists",
    ):
        manager.checkpoint(
            "task-1",
            "cp-1",
        )


def test_multiple_checkpoints_are_ordered_by_version(
    tmp_path: Path,
):
    manager = make_manager(tmp_path)

    manager.create_task(
        "task-1",
        "Analyze equipment",
    )

    first = manager.checkpoint(
        "task-1",
        "cp-1",
    )

    manager.start_task("task-1")

    second = manager.checkpoint(
        "task-1",
        "cp-2",
    )

    checkpoints = manager.list_checkpoints("task-1")

    assert len(checkpoints) == 2
    assert checkpoints[0].version == first.version
    assert checkpoints[1].version == second.version
    assert checkpoints[1].version > checkpoints[0].version


def test_latest_checkpoint_returns_latest(
    tmp_path: Path,
):
    manager = make_manager(tmp_path)

    manager.create_task(
        "task-1",
        "Analyze equipment",
    )

    manager.checkpoint(
        "task-1",
        "cp-1",
    )

    manager.start_task("task-1")

    manager.checkpoint(
        "task-1",
        "cp-2",
    )

    latest = manager.latest_checkpoint("task-1")

    assert latest is not None
    assert latest.checkpoint_id == "cp-2"


def test_checkpoint_survives_new_manager_instance(
    tmp_path: Path,
):
    database = tmp_path / "state.db"

    manager = AgentStateManager(
        store=DurableStateStore(database),
    )

    manager.create_task(
        "task-1",
        "Analyze equipment",
    )

    manager.start_task("task-1")

    manager.checkpoint(
        "task-1",
        "cp-1",
    )

    recovered_manager = AgentStateManager(
        store=DurableStateStore(database),
    )

    checkpoint = recovered_manager.latest_checkpoint(
        "task-1",
    )

    assert checkpoint is not None
    assert checkpoint.checkpoint_id == "cp-1"
    assert checkpoint.state.status.value == "running"


def test_missing_checkpoint_recovery_fails(
    tmp_path: Path,
):
    manager = make_manager(tmp_path)

    manager.create_task(
        "task-1",
        "Analyze equipment",
    )

    with pytest.raises(
        KeyError,
        match="No checkpoint found",
    ):
        manager.recover_latest_checkpoint("task-1")
