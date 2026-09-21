from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PlanStep:
    step_id: str
    tool_name: str
    description: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: PlanStepStatus = PlanStepStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanStep":
        payload = dict(data)
        payload["status"] = PlanStepStatus(
            payload.get("status", PlanStepStatus.PENDING.value)
        )
        return cls(**payload)


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    task_id: str = ""
    plan_id: str = field(
        default_factory=lambda: uuid4().hex
    )
    status: PlanStatus = PlanStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        return cls(
            plan_id=data["plan_id"],
            task_id=data.get("task_id", ""),
            goal=data["goal"],
            steps=[
                PlanStep.from_dict(step)
                for step in data.get("steps", [])
            ],
            status=PlanStatus(
                data.get("status", PlanStatus.PENDING.value)
            ),
            metadata=data.get("metadata", {}),
        )

    def get_step(self, step_id: str) -> PlanStep:
        for step in self.steps:
            if step.step_id == step_id:
                return step

        raise KeyError(f"Unknown plan step: {step_id}")
