from pathlib import Path

from app.state.manager import AgentStateManager
from app.state.models import TaskStatus, StepExecutionStatus
from app.state.store import DurableStateStore


def make_manager(tmp_path: Path) -> AgentStateManager:
    return AgentStateManager(
        DurableStateStore(tmp_path / "state.db")
    )


def test_full_crash_recovery_lifecycle(tmp_path):
    manager1 = make_manager(tmp_path)

    task = manager1.create_task(
        "industrial-task",
        "Analyze production data",
        "plan-001",
    )

    manager1.add_step(task.task_id, "retrieve")
    manager1.add_step(task.task_id, "analyze")
    manager1.add_step(task.task_id, "report")

    manager1.start_task(task.task_id)
    manager1.start_step(task.task_id, "retrieve")

    manager1.complete_step(
        task.task_id,
        "retrieve",
        {"documents": 12},
        {"source": "local"},
    )

    checkpoint = manager1.checkpoint(
        task.task_id,
        "cp-retrieve",
    )

    # Simulate process crash/restart.
    manager2 = make_manager(tmp_path)

    recovered = manager2.recover_latest_checkpoint(
        task.task_id
    )

    assert recovered.task_id == "industrial-task"
    assert recovered.goal == "Analyze production data"
    assert recovered.plan_id == "plan-001"
    assert recovered.status == TaskStatus.RUNNING

    assert (
        recovered.steps["retrieve"].status
        == StepExecutionStatus.COMPLETED
    )
    assert recovered.steps["retrieve"].result == {
        "documents": 12
    }

    assert (
        recovered.steps["analyze"].status
        == StepExecutionStatus.PENDING
    )
    assert (
        recovered.steps["report"].status
        == StepExecutionStatus.PENDING
    )

    assert recovered.version > checkpoint.version


def test_checkpoint_snapshot_is_immutable(tmp_path):
    manager = make_manager(tmp_path)

    task = manager.create_task(
        "task-1",
        "Immutable checkpoint",
    )

    manager.add_step(task.task_id, "step-1")
    manager.start_task(task.task_id)
    manager.start_step(task.task_id, "step-1")

    checkpoint = manager.checkpoint(
        task.task_id,
        "cp-1",
    )

    checkpoint.state.metadata["mutated"] = True

    stored = manager.get_checkpoint(
        task.task_id,
        "cp-1",
    )

    assert stored is not None
    assert "mutated" not in stored.state.metadata


def test_multiple_checkpoints_support_resume_history(tmp_path):
    manager = make_manager(tmp_path)

    task = manager.create_task(
        "task-1",
        "Checkpoint history",
    )

    manager.add_step(task.task_id, "step-1")
    manager.add_step(task.task_id, "step-2")

    manager.start_task(task.task_id)
    manager.start_step(task.task_id, "step-1")

    manager.complete_step(
        task.task_id,
        "step-1",
        {"value": 1},
        {},
    )

    cp1 = manager.checkpoint(
        task.task_id,
        "cp-1",
    )

    manager.start_step(task.task_id, "step-2")

    manager.complete_step(
        task.task_id,
        "step-2",
        {"value": 2},
        {},
    )

    cp2 = manager.checkpoint(
        task.task_id,
        "cp-2",
    )

    history = manager.list_checkpoints(
        task.task_id
    )

    assert len(history) == 2
    assert history[0].checkpoint_id == "cp-1"
    assert history[1].checkpoint_id == "cp-2"
    assert cp1.version < cp2.version

    latest = manager.latest_checkpoint(
        task.task_id
    )

    assert latest is not None
    assert latest.checkpoint_id == "cp-2"


def test_missing_checkpoint_fails_cleanly(tmp_path):
    manager = make_manager(tmp_path)

    manager.create_task(
        "task-1",
        "No checkpoint",
    )

    try:
        manager.recover_latest_checkpoint("task-1")
        assert False, "Expected missing checkpoint failure"
    except KeyError as exc:
        assert "No checkpoint found" in str(exc)
