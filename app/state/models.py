from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentStepState:
    step_id: str
    status: StepExecutionStatus = StepExecutionStatus.PENDING
    attempts: int = 0
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    observation: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "attempts": self.attempts,
            "result": self.result,
            "error": self.error,
            "observation": self.observation,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentStepState":
        return cls(
            step_id=data["step_id"],
            status=StepExecutionStatus(data["status"]),
            attempts=int(data.get("attempts", 0)),
            result=dict(data.get("result", {})),
            error=str(data.get("error", "")),
            observation=dict(data.get("observation", {})),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class AgentTaskState:
    task_id: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    plan_id: str | None = None
    current_step_id: str | None = None
    steps: dict[str, AgentStepState] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: int = 0

    def touch(self) -> None:
        previous = datetime.fromisoformat(self.updated_at)
        now = datetime.now(timezone.utc)

        if now <= previous:
            now = previous.replace(
                microsecond=previous.microsecond + 1
            )

        self.updated_at = now.isoformat()
        self.version += 1
        
    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": self.status.value,
            "plan_id": self.plan_id,
            "current_step_id": self.current_step_id,
            "steps": {
                step_id: step.to_dict()
                for step_id, step in self.steps.items()
            },
            "observations": self.observations,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentTaskState":
        return cls(
            task_id=data["task_id"],
            goal=data["goal"],
            status=TaskStatus(data["status"]),
            plan_id=data.get("plan_id"),
            current_step_id=data.get("current_step_id"),
            steps={
                step_id: AgentStepState.from_dict(step_data)
                for step_id, step_data in data.get("steps", {}).items()
            },
            observations=list(data.get("observations", [])),
            metadata=dict(data.get("metadata", {})),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            version=int(data.get("version", 0)),
        )


@dataclass(frozen=True)
class Checkpoint:
    task_id: str
    checkpoint_id: str
    version: int
    state: AgentTaskState
    created_at: str

    @classmethod
    def create(
        cls,
        task_id: str,
        checkpoint_id: str,
        state: AgentTaskState,
    ) -> "Checkpoint":
        return cls(
            task_id=task_id,
            checkpoint_id=checkpoint_id,
            version=state.version,
            state=state,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
