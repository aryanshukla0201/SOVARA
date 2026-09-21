from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class AuditEventType:
    TASK_CREATED = "task_created"
    PLAN_CREATED = "plan_created"
    POLICY_ALLOWED = "policy_allowed"
    POLICY_DENIED = "policy_denied"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    CHECKPOINT_CREATED = "checkpoint_created"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"
    APPROVAL_CANCELLED = "approval_cancelled"


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    task_id: str
    timestamp: str
    event_type: str
    tool_name: str = ""
    action: str = ""
    decision: str = ""
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_id: str,
        task_id: str,
        event_type: str,
        tool_name: str = "",
        action: str = "",
        decision: str = "",
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "AuditEvent":
        return cls(
            event_id=event_id,
            task_id=task_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            tool_name=tool_name,
            action=action,
            decision=decision,
            reason=reason,
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "tool_name": self.tool_name,
            "action": self.action,
            "decision": self.decision,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEvent":
        return cls(
            event_id=data["event_id"],
            task_id=data["task_id"],
            timestamp=data["timestamp"],
            event_type=data["event_type"],
            tool_name=str(data.get("tool_name", "")),
            action=str(data.get("action", "")),
            decision=str(data.get("decision", "")),
            reason=str(data.get("reason", "")),
            metadata=dict(data.get("metadata", {})),
        )
