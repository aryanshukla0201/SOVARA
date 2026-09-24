from __future__ import annotations

from dataclasses import dataclass

from app.governance.models import Policy, RiskLevel
from app.tools.registry import ToolSpec


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    _RISK_ORDER = {
        RiskLevel.LOW.value: 0,
        RiskLevel.MEDIUM.value: 1,
        RiskLevel.HIGH.value: 2,
        RiskLevel.CRITICAL.value: 3,
    }

    def evaluate(
        self,
        spec: ToolSpec,
        policy: Policy,
    ) -> PolicyDecision:
        if not policy.enabled:
            return PolicyDecision(
                allowed=False,
                reason="policy is disabled",
            )

        if not spec.enabled:
            return PolicyDecision(
                allowed=False,
                reason=f"tool {spec.tool_name} is disabled",
            )

        if spec.tool_name in policy.denied_tools:
            return PolicyDecision(
                allowed=False,
                reason=f"tool {spec.tool_name} is denied by policy",
            )

        if (
            policy.allowed_tools
            and spec.tool_name not in policy.allowed_tools
        ):
            return PolicyDecision(
                allowed=False,
                reason=f"tool {spec.tool_name} is not permitted by policy",
            )

        if (
            policy.allowed_execution_methods
            and spec.execution_method
            not in policy.allowed_execution_methods
        ):
            return PolicyDecision(
                allowed=False,
                reason=(
                    "execution method "
                    f"{spec.execution_method} is not permitted by policy"
                ),
            )

        unauthorized_permissions = sorted(
            set(spec.permissions) - policy.allowed_permissions
        )

        if policy.allowed_permissions and unauthorized_permissions:
            return PolicyDecision(
                allowed=False,
                reason=(
                    "permissions not permitted by policy: "
                    + ", ".join(unauthorized_permissions)
                ),
            )

        tool_risk = self._RISK_ORDER.get(spec.risk_level)

        if tool_risk is None:
            return PolicyDecision(
                allowed=False,
                reason=f"unknown risk level: {spec.risk_level}",
            )

        maximum_risk = self._RISK_ORDER[policy.max_risk_level.value]

        if tool_risk > maximum_risk:
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"risk level {spec.risk_level} exceeds "
                    f"policy maximum {policy.max_risk_level.value}"
                ),
            )

        if spec.timeout_seconds > policy.max_timeout_seconds:
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"timeout {spec.timeout_seconds}s exceeds "
                    f"policy maximum {policy.max_timeout_seconds}s"
                ),
            )

        if spec.timeout_seconds <= 0:
            return PolicyDecision(
                allowed=False,
                reason="timeout must be greater than zero",
            )

        if (
            policy.approval_required_for_risk is not None
            and tool_risk
            >= self._RISK_ORDER[
                policy.approval_required_for_risk.value
            ]
        ):
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"risk level {spec.risk_level} requires approval "
                    "before execution"
                ),
            )

        return PolicyDecision(
            allowed=True,
            reason="tool permitted by policy",
        )
