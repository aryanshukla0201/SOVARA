from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionMethod(str, Enum):
    LOCAL = "local"
    SANDBOX = "sandbox"
    REMOTE = "remote"


@dataclass(frozen=True)
class Policy:
    name: str = "default"
    enabled: bool = True
    allowed_tools: frozenset[str] = frozenset()
    denied_tools: frozenset[str] = frozenset()
    allowed_permissions: frozenset[str] = frozenset()
    allowed_execution_methods: frozenset[str] = frozenset()
    max_risk_level: RiskLevel = RiskLevel.MEDIUM
    max_timeout_seconds: int = 120
    approval_required_for_risk: RiskLevel | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Policy name must not be empty.")

        if self.max_timeout_seconds <= 0:
            raise ValueError(
                "max_timeout_seconds must be greater than zero."
            )

        if (
            self.approval_required_for_risk is not None
            and self.approval_required_for_risk == RiskLevel.LOW
        ):
            raise ValueError(
                "approval_required_for_risk must be above low risk."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "allowed_tools": sorted(self.allowed_tools),
            "denied_tools": sorted(self.denied_tools),
            "allowed_permissions": sorted(self.allowed_permissions),
            "allowed_execution_methods": sorted(
                self.allowed_execution_methods
            ),
            "max_risk_level": self.max_risk_level.value,
            "max_timeout_seconds": self.max_timeout_seconds,
            "approval_required_for_risk": (
                self.approval_required_for_risk.value
                if self.approval_required_for_risk is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Policy":
        return cls(
            name=data.get("name", "default"),
            enabled=data.get("enabled", True),
            allowed_tools=frozenset(data.get("allowed_tools", [])),
            denied_tools=frozenset(data.get("denied_tools", [])),
            allowed_permissions=frozenset(
                data.get("allowed_permissions", [])
            ),
            allowed_execution_methods=frozenset(
                data.get("allowed_execution_methods", [])
            ),
            max_risk_level=RiskLevel(
                data.get("max_risk_level", RiskLevel.MEDIUM.value)
            ),
            max_timeout_seconds=data.get("max_timeout_seconds", 120),
            approval_required_for_risk=(
                RiskLevel(data["approval_required_for_risk"])
                if data.get("approval_required_for_risk") is not None
                else None
            ),
        )
