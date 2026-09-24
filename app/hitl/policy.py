from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class ApprovalPolicy:
    name: str = "default-approval"
    enabled: bool = True
    approval_required: bool = False
    risk_levels_requiring_approval: frozenset[str] = frozenset({"high", "critical"})
    sensitive_permissions: frozenset[str] = frozenset()
    destructive_actions: frozenset[str] = frozenset()
    external_side_effects: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be empty")


@dataclass(frozen=True)
class ApprovalDecision:
    approval_required: bool
    reason: str
    triggers: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class ApprovalPolicyEngine:
    def evaluate(
        self,
        *,
        risk_level: str,
        permissions: Iterable[str] = (),
        action: str = "",
        external_side_effect: bool = False,
        policy: ApprovalPolicy,
    ) -> ApprovalDecision:
        if not policy.enabled:
            return ApprovalDecision(
                approval_required=False,
                reason="approval policy is disabled",
            )

        triggers: list[str] = []

        if policy.approval_required:
            triggers.append("policy_requires_approval")

        if risk_level in policy.risk_levels_requiring_approval:
            triggers.append("risk_level")

        sensitive = sorted(
            set(permissions).intersection(policy.sensitive_permissions)
        )
        if sensitive:
            triggers.append("sensitive_permission")

        if action in policy.destructive_actions:
            triggers.append("destructive_action")

        if policy.external_side_effects and external_side_effect:
            triggers.append("external_side_effect")

        if triggers:
            return ApprovalDecision(
                approval_required=True,
                reason="human approval is required",
                triggers=tuple(triggers),
                metadata={
                    "risk_level": risk_level,
                    "sensitive_permissions": sensitive,
                    "action": action,
                    "external_side_effect": external_side_effect,
                },
            )

        return ApprovalDecision(
            approval_required=False,
            reason="human approval is not required",
        )
