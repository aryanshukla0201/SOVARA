from __future__ import annotations

from app.state.checkpoints import CheckpointStore
from app.state.models import (
    AgentStepState,
    AgentTaskState,
    Checkpoint,
    StepExecutionStatus,
    TaskStatus,
)
from app.state.store import DurableStateStore


class AgentStateManager:
    def __init__(
        self,
        store: DurableStateStore | None = None,
        checkpoints: CheckpointStore | None = None,
    ) -> None:
        self.store = store or DurableStateStore()
        self.checkpoints = checkpoints or CheckpointStore(
            self.store.database_path
        )

    def create_task(
        self,
        task_id: str,
        goal: str,
        plan_id: str | None = None,
    ) -> AgentTaskState:
        if not task_id.strip():
            raise ValueError("task_id must not be empty")

        if not goal.strip():
            raise ValueError("goal must not be empty")

        if self.store.exists(task_id):
            raise ValueError(
                f"Task already exists: {task_id}"
            )

        state = AgentTaskState(
            task_id=task_id,
            goal=goal,
            plan_id=plan_id,
            status=TaskStatus.PENDING,
        )

        return self.store.save(state)

    def get_task(self, task_id: str) -> AgentTaskState | None:
        return self.store.get(task_id)

    def require_task(self, task_id: str) -> AgentTaskState:
        state = self.get_task(task_id)

        if state is None:
            raise KeyError(f"Task not found: {task_id}")

        return state

    def add_step(
        self,
        task_id: str,
        step_id: str,
    ) -> AgentTaskState:
        state = self.require_task(task_id)

        if not step_id.strip():
            raise ValueError("step_id must not be empty")

        if step_id in state.steps:
            raise ValueError(
                f"Step already exists: {step_id}"
            )

        previous_version = state.version

        state.steps[step_id] = AgentStepState(
            step_id=step_id,
        )
        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def start_task(self, task_id: str) -> AgentTaskState:
        state = self.require_task(task_id)

        if state.status not in {
            TaskStatus.PENDING,
            TaskStatus.FAILED,
        }:
            raise ValueError(
                f"Task cannot start from status: {state.status.value}"
            )

        previous_version = state.version

        state.status = TaskStatus.RUNNING
        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def start_step(
        self,
        task_id: str,
        step_id: str,
    ) -> AgentTaskState:
        state = self.require_task(task_id)

        if state.status != TaskStatus.RUNNING:
            raise ValueError(
                "Task must be running before starting a step."
            )

        step = state.steps.get(step_id)

        if step is None:
            raise KeyError(
                f"Step not found: {step_id}"
            )

        if step.status not in {
            StepExecutionStatus.PENDING,
            StepExecutionStatus.FAILED,
        }:
            raise ValueError(
                f"Step cannot start from status: "
                f"{step.status.value}"
            )

        previous_version = state.version

        step.status = StepExecutionStatus.RUNNING
        step.attempts += 1
        step.started_at = state.updated_at
        state.current_step_id = step_id
        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def complete_step(
        self,
        task_id: str,
        step_id: str,
        result: dict,
        observation: dict | None = None,
    ) -> AgentTaskState:
        state = self.require_task(task_id)
        step = state.steps.get(step_id)

        if step is None:
            raise KeyError(
                f"Step not found: {step_id}"
            )

        if step.status != StepExecutionStatus.RUNNING:
            raise ValueError(
                "Only a running step can be completed."
            )

        previous_version = state.version

        step.status = StepExecutionStatus.COMPLETED
        step.result = dict(result)
        step.observation = dict(observation or {})
        step.completed_at = state.updated_at

        if state.current_step_id == step_id:
            state.current_step_id = None

        state.observations.append(
            {
                "step_id": step_id,
                "type": "completion",
                "observation": dict(observation or {}),
            }
        )

        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def fail_step(
        self,
        task_id: str,
        step_id: str,
        error: str,
        observation: dict | None = None,
    ) -> AgentTaskState:
        state = self.require_task(task_id)
        step = state.steps.get(step_id)

        if step is None:
            raise KeyError(
                f"Step not found: {step_id}"
            )

        if step.status != StepExecutionStatus.RUNNING:
            raise ValueError(
                "Only a running step can fail."
            )

        previous_version = state.version

        step.status = StepExecutionStatus.FAILED
        step.error = error
        step.observation = dict(observation or {})
        step.completed_at = state.updated_at

        state.observations.append(
            {
                "step_id": step_id,
                "type": "failure",
                "error": error,
                "observation": dict(observation or {}),
            }
        )

        state.current_step_id = None
        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def complete_task(
        self,
        task_id: str,
    ) -> AgentTaskState:
        state = self.require_task(task_id)

        incomplete = [
            step_id
            for step_id, step in state.steps.items()
            if step.status not in {
                StepExecutionStatus.COMPLETED,
                StepExecutionStatus.SKIPPED,
            }
        ]

        if incomplete:
            raise ValueError(
                "Cannot complete task with incomplete steps: "
                + ", ".join(incomplete)
            )

        previous_version = state.version

        state.status = TaskStatus.COMPLETED
        state.current_step_id = None
        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def fail_task(
        self,
        task_id: str,
    ) -> AgentTaskState:
        state = self.require_task(task_id)

        previous_version = state.version

        state.status = TaskStatus.FAILED
        state.current_step_id = None
        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def cancel_task(
        self,
        task_id: str,
    ) -> AgentTaskState:
        state = self.require_task(task_id)

        if state.status in {
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
        }:
            raise ValueError(
                f"Task cannot be cancelled from status: "
                f"{state.status.value}"
            )

        previous_version = state.version

        state.status = TaskStatus.CANCELLED
        state.current_step_id = None
        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def checkpoint(
        self,
        task_id: str,
        checkpoint_id: str,
    ) -> Checkpoint:
        state = self.require_task(task_id)

        if not checkpoint_id.strip():
            raise ValueError(
                "checkpoint_id must not be empty"
            )

        checkpoint = Checkpoint.create(
            task_id=task_id,
            checkpoint_id=checkpoint_id,
            state=state,
        )

        return self.checkpoints.save(checkpoint)

    def get_checkpoint(
        self,
        task_id: str,
        checkpoint_id: str,
    ) -> Checkpoint | None:
        return self.checkpoints.get(
            task_id,
            checkpoint_id,
        )

    def latest_checkpoint(
        self,
        task_id: str,
    ) -> Checkpoint | None:
        return self.checkpoints.latest(task_id)

    def list_checkpoints(
        self,
        task_id: str,
    ) -> list[Checkpoint]:
        return self.checkpoints.list_for_task(task_id)

    def resume(
        self,
        task_id: str,
    ) -> AgentTaskState:
        state = self.require_task(task_id)

        if state.status == TaskStatus.CANCELLED:
            raise ValueError(
                "Cancelled tasks cannot be resumed."
            )

        if state.status == TaskStatus.COMPLETED:
            raise ValueError(
                "Completed tasks cannot be resumed."
            )

        previous_version = state.version

        state.status = TaskStatus.RUNNING
        state.touch()

        return self.store.save(
            state,
            expected_version=previous_version,
        )

    def recover_latest_checkpoint(
        self,
        task_id: str,
    ) -> AgentTaskState:
        checkpoint = self.latest_checkpoint(task_id)

        if checkpoint is None:
            raise KeyError(
                f"No checkpoint found for task: {task_id}"
            )

        current = self.get_task(task_id)

        recovered = checkpoint.state

        if current is not None:
            expected_version = current.version

            # Recovery is a new durable state transition.
            # Preserve the checkpoint snapshot while assigning it
            # the next monotonic version after the current state.
            recovered.version = current.version + 1
            recovered.touch()

            # touch() increments version, so restore the exact
            # next durable version after updating its timestamp.
            recovered.version = current.version + 1

            return self.store.save(
                recovered,
                expected_version=expected_version,
            )

        recovered.touch()

        return self.store.save(recovered)
