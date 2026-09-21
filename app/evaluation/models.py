from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VerificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    check: str
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == VerificationStatus.PASSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "check": self.check,
            "reason": self.reason,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationResult":
        return cls(
            status=VerificationStatus(data["status"]),
            check=data["check"],
            reason=data.get("reason", ""),
            details=dict(data.get("details", {})),
        )


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    name: str
    input_data: dict[str, Any] = field(default_factory=dict)
    expected_output: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "input_data": dict(self.input_data),
            "expected_output": self.expected_output,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationCase":
        return cls(
            case_id=data["case_id"],
            name=data["name"],
            input_data=dict(data.get("input_data", {})),
            expected_output=data.get("expected_output"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    passed: bool
    actual_output: Any = None
    expected_output: Any = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "actual_output": self.actual_output,
            "expected_output": self.expected_output,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationResult":
        return cls(
            case_id=data["case_id"],
            passed=bool(data["passed"]),
            actual_output=data.get("actual_output"),
            expected_output=data.get("expected_output"),
            reason=data.get("reason", ""),
        )


@dataclass(frozen=True)
class EvaluationSummary:
    total: int
    passed: int
    failed: int
    results: tuple[EvaluationResult, ...] = ()

    @property
    def success(self) -> bool:
        return self.total > 0 and self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "results": [result.to_dict() for result in self.results],
        }
