from pathlib import Path

import pytest

from app.state.manager import AgentStateManager
from app.state.models import (
    StepExecutionStatus,
    TaskStatus,
)
from app.state.store import DurableStateStore


def make_manager(tmp_path: Path) -> AgentStateManager:
    return AgentStateManager(
        DurableStateStore(tmp_path / "state.db")
    )


def test_create_task(tmp_path: Path):
    manager = make_manager(tmp_path)

    state = manager.create_task(
        "task-1",
        "Analyze equipment",
        "plan-1",
    )

    assert state.task_id == "task-1"
    assert state.goal == "Analyze equipment"
    assert state.plan_id == "plan-1"
    assert state.status == TaskStatus.PENDING


def test_duplicate_task_is_rejected(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")

    with pytest.raises(ValueError, match="already exists"):
        manager.create_task("task-1", "Analyze again")


def test_add_step(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")

    state = manager.add_step("task-1", "step-1")

    assert "step-1" in state.steps
    assert state.steps["step-1"].status == StepExecutionStatus.PENDING


def test_task_lifecycle(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")
    manager.add_step("task-1", "step-1")

    state = manager.start_task("task-1")

    assert state.status == TaskStatus.RUNNING

    state = manager.start_step("task-1", "step-1")

    assert state.current_step_id == "step-1"
    assert state.steps["step-1"].status == StepExecutionStatus.RUNNING
    assert state.steps["step-1"].attempts == 1

    state = manager.complete_step(
        "task-1",
        "step-1",
        {"answer": 42},
        {"verified": True},
    )

    assert state.steps["step-1"].status == StepExecutionStatus.COMPLETED
    assert state.steps["step-1"].result["answer"] == 42
    assert state.current_step_id is None

    state = manager.complete_task("task-1")

    assert state.status == TaskStatus.COMPLETED


def test_failed_step(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")
    manager.add_step("task-1", "step-1")
    manager.start_task("task-1")
    manager.start_step("task-1", "step-1")

    state = manager.fail_step(
        "task-1",
        "step-1",
        "tool failed",
        {"retryable": True},
    )

    assert state.steps["step-1"].status == StepExecutionStatus.FAILED
    assert state.steps["step-1"].error == "tool failed"
    assert state.current_step_id is None


def test_incomplete_task_cannot_complete(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")
    manager.add_step("task-1", "step-1")
    manager.start_task("task-1")

    with pytest.raises(ValueError, match="incomplete"):
        manager.complete_task("task-1")


def test_checkpoint(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")

    checkpoint = manager.checkpoint(
        "task-1",
        "checkpoint-1",
    )

    assert checkpoint.task_id == "task-1"
    assert checkpoint.checkpoint_id == "checkpoint-1"
    assert checkpoint.state.task_id == "task-1"


def test_resume(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")
    manager.start_task("task-1")
    manager.fail_task("task-1")

    state = manager.resume("task-1")

    assert state.status == TaskStatus.RUNNING


def test_cancelled_task_cannot_resume(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")
    manager.cancel_task("task-1")

    with pytest.raises(ValueError, match="Cancelled"):
        manager.resume("task-1")


def test_completed_task_cannot_resume(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_task("task-1", "Analyze equipment")
    manager.complete_task("task-1")

    with pytest.raises(ValueError, match="Completed"):
        manager.resume("task-1")


def test_missing_task_is_rejected(tmp_path: Path):
    manager = make_manager(tmp_path)

    with pytest.raises(KeyError, match="not found"):
        manager.require_task("missing")
