from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionPolicy:
    allowed_permissions: frozenset[str] = frozenset({
        "local_documents",
        "local_files",
        "local_images",
        "sandbox_execution",
    })

    allowed_execution_methods: frozenset[str] = frozenset({
        "local",
        "sandbox",
    })

    maximum_risk_level: str = "medium"
    maximum_timeout_seconds: int = 120


class ExecutionPolicyEnforcer:
    _RISK_ORDER = {
        "low": 0,
        "medium": 1,
        "high": 2,
        "critical": 3,
    }

    def __init__(
        self,
        policy: ExecutionPolicy | None = None,
    ) -> None:
        self.policy = policy or ExecutionPolicy()

    def validate(self, spec) -> list[str]:
        errors: list[str] = []

        if not spec.enabled:
            errors.append(
                f"Tool is disabled: {spec.tool_name}"
            )

        if spec.execution_method not in self.policy.allowed_execution_methods:
            errors.append(
                "Execution method is not allowed: "
                f"{spec.execution_method}"
            )

        if spec.risk_level not in self._RISK_ORDER:
            errors.append(
                f"Invalid risk level: {spec.risk_level}"
            )
        elif (
            self._RISK_ORDER[spec.risk_level]
            > self._RISK_ORDER[self.policy.maximum_risk_level]
        ):
            errors.append(
                f"Risk level is not allowed: {spec.risk_level}"
            )

        unauthorized = sorted(
            set(spec.permissions)
            - set(self.policy.allowed_permissions)
        )

        for permission in unauthorized:
            errors.append(
                f"Permission is not allowed: {permission}"
            )

        if spec.timeout_seconds > self.policy.maximum_timeout_seconds:
            errors.append(
                "Timeout exceeds policy maximum: "
                f"{spec.timeout_seconds}s"
            )

        if spec.timeout_seconds <= 0:
            errors.append(
                "Timeout must be greater than zero."
            )

        return errors

    def is_allowed(self, spec) -> bool:
        return not self.validate(spec)
