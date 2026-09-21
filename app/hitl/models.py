from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    task_id: str
    step_id: str
    tool_name: str
    reason: str
    risk_level: str
    requested_action: str
    requested_arguments_summary: str
    created_at: str
    expires_at: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            "approval_id": self.approval_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "requested_action": self.requested_action,
            "created_at": self.created_at,
        }

        for field_name, value in required.items():
            if not str(value).strip():
                raise ValueError(f"{field_name} must not be empty")

        if self.expires_at is not None and not str(self.expires_at).strip():
            raise ValueError("expires_at must not be empty when provided")

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "requested_action": self.requested_action,
            "requested_arguments_summary": self.requested_arguments_summary,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRequest:
        return cls(
            approval_id=str(data["approval_id"]),
            task_id=str(data["task_id"]),
            step_id=str(data["step_id"]),
            tool_name=str(data["tool_name"]),
            reason=str(data["reason"]),
            risk_level=str(data["risk_level"]),
            requested_action=str(data["requested_action"]),
            requested_arguments_summary=str(
                data.get("requested_arguments_summary", "")
            ),
            created_at=str(data["created_at"]),
            expires_at=data.get("expires_at"),
            status=ApprovalStatus(data.get("status", ApprovalStatus.PENDING.value)),
            metadata=dict(data.get("metadata", {})),
        )
