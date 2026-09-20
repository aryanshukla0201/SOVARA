from pathlib import Path

from app.state.manager import AgentStateManager
from app.state.models import TaskStatus, StepExecutionStatus
from app.state.store import DurableStateStore


def make_manager(tmp_path: Path) -> AgentStateManager:
    return AgentStateManager(
        DurableStateStore(tmp_path / "state.db")
    )


def test_resume_restores_checkpoint_state(tmp_path):
    manager = make_manager(tmp_path)

    task = manager.create_task("task-1", "Process document")
    manager.add_step(task.task_id, "step-1")
    manager.add_step(task.task_id, "step-2")

    manager.start_task(task.task_id)
    manager.start_step(task.task_id, "step-1")

    manager.complete_step(
        task.task_id,
        "step-1",
        {"value": 42},
        {"source": "test"},
    )

    checkpoint = manager.checkpoint(
        task.task_id,
        "checkpoint-1",
    )

    manager.start_step(task.task_id, "step-2")

    recovered = manager.recover_latest_checkpoint(task.task_id)

    assert recovered.task_id == task.task_id
    assert recovered.goal == "Process document"
    assert recovered.status == TaskStatus.RUNNING
    assert recovered.steps["step-1"].status == StepExecutionStatus.COMPLETED
    assert recovered.steps["step-1"].result == {"value": 42}
    assert recovered.steps["step-2"].status == StepExecutionStatus.PENDING
    assert recovered.current_step_id is None
    assert recovered.version > checkpoint.version


def test_resume_after_new_manager_instance(tmp_path):
    manager1 = make_manager(tmp_path)

    task = manager1.create_task("task-1", "Persistent task")
    manager1.add_step(task.task_id, "step-1")
    manager1.start_task(task.task_id)
    manager1.start_step(task.task_id, "step-1")

    checkpoint = manager1.checkpoint(
        task.task_id,
        "checkpoint-1",
    )

    manager2 = make_manager(tmp_path)

    recovered = manager2.recover_latest_checkpoint(task.task_id)

    assert recovered.task_id == task.task_id
    assert recovered.goal == "Persistent task"
    assert recovered.status == TaskStatus.RUNNING
    assert recovered.current_step_id == "step-1"
    assert recovered.steps["step-1"].status == StepExecutionStatus.RUNNING
    assert recovered.version > checkpoint.version


def test_failed_step_can_be_recovered_from_checkpoint(tmp_path):
    manager = make_manager(tmp_path)

    task = manager.create_task(
        "task-1",
        "Recover failed execution",
    )
    manager.add_step(task.task_id, "step-1")
    manager.start_task(task.task_id)
    manager.start_step(task.task_id, "step-1")

    manager.fail_step(
        task.task_id,
        "step-1",
        "temporary failure",
    )

    checkpoint = manager.checkpoint(
        task.task_id,
        "checkpoint-1",
    )

    # Advance the durable state with a valid lifecycle transition:
    # retry the failed step.
    manager.start_step(task.task_id, "step-1")

    current = manager.get_task(task.task_id)
    assert current.steps["step-1"].status == StepExecutionStatus.RUNNING
    assert current.version > checkpoint.version

    recovered = manager.recover_latest_checkpoint(task.task_id)

    assert recovered.status == TaskStatus.RUNNING
    assert recovered.steps["step-1"].status == StepExecutionStatus.FAILED
    assert recovered.steps["step-1"].error == "temporary failure"
    assert recovered.version > current.version


def test_recovery_creates_new_durable_version(tmp_path):
    manager = make_manager(tmp_path)

    task = manager.create_task(
        "task-1",
        "Version recovery",
    )
    manager.add_step(task.task_id, "step-1")
    manager.start_task(task.task_id)

    checkpoint = manager.checkpoint(
        task.task_id,
        "checkpoint-1",
    )

    current = manager.get_task(task.task_id)
    current_version = current.version

    recovered = manager.recover_latest_checkpoint(task.task_id)

    assert recovered.version > current_version

    persisted = manager.get_task(task.task_id)

    assert persisted.version == recovered.version
    assert persisted.version > checkpoint.version
