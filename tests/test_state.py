from __future__ import annotations

from pathlib import Path

from app.state.models import (
    AgentStepState,
    AgentTaskState,
    StepExecutionStatus,
    TaskStatus,
)
from app.state.store import DurableStateStore


def make_state(task_id: str = "task-1") -> AgentTaskState:
    return AgentTaskState(
        task_id=task_id,
        goal="Analyze the equipment data",
        plan_id="plan-1",
        steps={
            "step-1": AgentStepState(
                step_id="step-1",
            ),
            "step-2": AgentStepState(
                step_id="step-2",
                status=StepExecutionStatus.COMPLETED,
                attempts=1,
                result={"value": 42},
            ),
        },
    )


def test_state_round_trip():
    state = make_state()

    restored = AgentTaskState.from_dict(state.to_dict())

    assert restored.to_dict() == state.to_dict()


def test_step_round_trip():
    step = AgentStepState(
        step_id="step-1",
        status=StepExecutionStatus.FAILED,
        attempts=2,
        result={"partial": True},
        error="tool failed",
        observation={"retryable": True},
    )

    restored = AgentStepState.from_dict(step.to_dict())

    assert restored.to_dict() == step.to_dict()


def test_store_save_and_get(tmp_path: Path):
    store = DurableStateStore(tmp_path / "state.db")
    state = make_state()

    store.save(state)

    restored = store.get(state.task_id)

    assert restored is not None
    assert restored.to_dict() == state.to_dict()


def test_store_survives_new_process_instance(tmp_path: Path):
    database = tmp_path / "state.db"

    state = make_state()

    DurableStateStore(database).save(state)

    second_store = DurableStateStore(database)

    restored = second_store.get(state.task_id)

    assert restored is not None
    assert restored.task_id == state.task_id
    assert restored.plan_id == "plan-1"
    assert restored.steps["step-2"].result["value"] == 42


def test_missing_state_returns_none(tmp_path: Path):
    store = DurableStateStore(tmp_path / "state.db")

    assert store.get("missing") is None


def test_version_must_increase(tmp_path: Path):
    store = DurableStateStore(tmp_path / "state.db")
    state = make_state()

    store.save(state)

    with __import__("pytest").raises(ValueError, match="must increase"):
        store.save(state)


def test_expected_version_prevents_stale_write(tmp_path: Path):
    store = DurableStateStore(tmp_path / "state.db")

    state = make_state()
    store.save(state)

    stale = store.get(state.task_id)
    assert stale is not None

    fresh = store.get(state.task_id)
    assert fresh is not None

    fresh.touch()
    store.save(fresh, expected_version=0)

    stale.touch()

    with __import__("pytest").raises(
        ValueError,
        match="version conflict",
    ):
        store.save(
            stale,
            expected_version=0,
        )


def test_delete(tmp_path: Path):
    store = DurableStateStore(tmp_path / "state.db")
    state = make_state()

    store.save(state)
    assert store.exists(state.task_id)

    store.delete(state.task_id)

    assert not store.exists(state.task_id)


def test_state_touch_increments_version():
    state = make_state()

    assert state.version == 0

    state.touch()

    assert state.version == 1
    assert state.updated_at != state.created_at


def test_status_values_are_stable():
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"

    assert StepExecutionStatus.PENDING.value == "pending"
    assert StepExecutionStatus.RUNNING.value == "running"
    assert StepExecutionStatus.COMPLETED.value == "completed"
    assert StepExecutionStatus.FAILED.value == "failed"
    assert StepExecutionStatus.SKIPPED.value == "skipped"
