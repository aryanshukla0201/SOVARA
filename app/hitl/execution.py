from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.execution.broker import ExecutionBroker, ExecutionRequest, ExecutionResult
from app.governance.audit import AuditEvent, AuditEventType
from app.hitl.manager import (
    ApprovalManager,
    ApprovalNotFoundError,
    ApprovalTransitionError,
)
from app.hitl.models import ApprovalRequest, ApprovalStatus
from app.hitl.policy import ApprovalPolicy, ApprovalPolicyEngine


@dataclass(frozen=True)
class ApprovalExecutionResult:
    status: str
    approval_required: bool
    approval_id: str | None = None
    execution_result: ExecutionResult | None = None
    error: str = ""

    @property
    def executed(self) -> bool:
        return self.execution_result is not None


class ApprovalExecutionGate:
    """
    Human-in-the-loop gate around the existing ExecutionBroker.

    P7 remains authoritative for execution permission.
    P9 decides whether a human approval is required before execution.
    Approved requests are always sent through ExecutionBroker, preserving P5.
    """

    def __init__(
        self,
        broker: ExecutionBroker,
        approval_manager: ApprovalManager | None = None,
        approval_policy: ApprovalPolicy | None = None,
        approval_policy_engine: ApprovalPolicyEngine | None = None,
    ) -> None:
        self.broker = broker
        self.approval_manager = approval_manager or ApprovalManager()
        self.approval_policy = approval_policy or ApprovalPolicy()
        self.approval_policy_engine = (
            approval_policy_engine or ApprovalPolicyEngine()
        )

    def _record(
        self,
        request: ExecutionRequest,
        event_type: str,
        *,
        approval_id: str = "",
        decision: str = "",
        reason: str = "",
    ) -> None:
        self.broker.observability.record(
            AuditEvent.create(
                event_id=str(uuid4()),
                task_id=request.task_id,
                event_type=event_type,
                tool_name=request.tool_name,
                action="approval",
                decision=decision,
                reason=reason,
                metadata={
                    "approval_id": approval_id,
                    "step_id": request.arguments.get("_step_id", ""),
                },
            )
        )

    def _approval_decision(
        self,
        request: ExecutionRequest,
    ):
        try:
            spec = self.broker.registry.get(request.tool_name)
        except KeyError:
            return None, None

        governance_decision = self.broker.policy_engine.evaluate(
            spec,
            self.broker.governance_policy,
        )

        if not governance_decision.allowed:
            return governance_decision, None

        risk_level = getattr(spec, "risk_level", "low")
        permissions = getattr(spec, "permissions", ())
        action = str(getattr(spec, "action", request.tool_name))
        external_side_effect = bool(
            getattr(spec, "external_side_effect", False)
        )

        decision = self.approval_policy_engine.evaluate(
            risk_level=risk_level,
            permissions=permissions,
            action=action,
            external_side_effect=external_side_effect,
            policy=self.approval_policy,
        )

        return governance_decision, decision

    def submit(
        self,
        request: ExecutionRequest,
        *,
        step_id: str = "",
    ) -> ApprovalExecutionResult:
        arguments = dict(request.arguments)

        if step_id:
            arguments["_step_id"] = step_id

        gated_request = ExecutionRequest(
            tool_name=request.tool_name,
            arguments=arguments,
            task_id=request.task_id,
        )

        governance_decision, approval_decision = self._approval_decision(
            gated_request
        )

        if governance_decision is not None and not governance_decision.allowed:
            return ApprovalExecutionResult(
                status="rejected",
                approval_required=False,
                error=governance_decision.reason,
            )

        if approval_decision is None or not approval_decision.approval_required:
            return ApprovalExecutionResult(
                status="executed",
                approval_required=False,
                execution_result=self.broker.execute(gated_request),
            )

        approval = self.approval_manager.create_request(
            task_id=gated_request.task_id,
            step_id=step_id or "unknown",
            tool_name=gated_request.tool_name,
            reason=approval_decision.reason,
            risk_level=str(
                getattr(
                    self.broker.registry.get(gated_request.tool_name),
                    "risk_level",
                    "unknown",
                )
            ),
            requested_action=gated_request.tool_name,
            requested_arguments_summary="execution request submitted for approval",
        )

        self._record(
            gated_request,
            AuditEventType.APPROVAL_REQUESTED,
            approval_id=approval.approval_id,
            decision="pending",
            reason=approval.reason,
        )

        return ApprovalExecutionResult(
            status="pending",
            approval_required=True,
            approval_id=approval.approval_id,
        )

    def approve_and_execute(
        self,
        approval_id: str,
    ) -> ApprovalExecutionResult:
        approval = self.approval_manager.approve(approval_id)

        request = ExecutionRequest(
            tool_name=approval.tool_name,
            arguments={},
            task_id=approval.task_id,
        )

        self._record(
            request,
            AuditEventType.APPROVAL_APPROVED,
            approval_id=approval.approval_id,
            decision="approve",
            reason="human approval granted",
        )

        result = self.broker.execute(request)

        return ApprovalExecutionResult(
            status="executed" if result.success else "failed",
            approval_required=True,
            approval_id=approval.approval_id,
            execution_result=result,
            error=result.error,
        )

    def reject(self, approval_id: str, reason: str = "") -> ApprovalRequest:
        approval = self.approval_manager.reject(approval_id)

        request = ExecutionRequest(
            tool_name=approval.tool_name,
            task_id=approval.task_id,
        )

        self._record(
            request,
            AuditEventType.APPROVAL_REJECTED,
            approval_id=approval.approval_id,
            decision="reject",
            reason=reason or "human approval rejected",
        )

        return approval

    def cancel(self, approval_id: str, reason: str = "") -> ApprovalRequest:
        approval = self.approval_manager.cancel(approval_id)

        request = ExecutionRequest(
            tool_name=approval.tool_name,
            task_id=approval.task_id,
        )

        self._record(
            request,
            AuditEventType.APPROVAL_CANCELLED,
            approval_id=approval.approval_id,
            decision="cancel",
            reason=reason or "approval cancelled",
        )

        return approval

    def expire(self, approval_id: str) -> ApprovalRequest:
        approval = self.approval_manager.expire(approval_id)

        request = ExecutionRequest(
            tool_name=approval.tool_name,
            task_id=approval.task_id,
        )

        self._record(
            request,
            AuditEventType.APPROVAL_EXPIRED,
            approval_id=approval.approval_id,
            decision="expire",
            reason="approval expired",
        )

        return approval

    def execute_approved(
        self,
        approval_id: str,
        arguments: dict[str, Any] | None = None,
    ) -> ApprovalExecutionResult:
        """
        Execute an already-approved request.

        This method deliberately requires APPROVED state and still routes
        execution through ExecutionBroker.
        """
        approval = self.approval_manager.get(approval_id)

        if approval.status is not ApprovalStatus.APPROVED:
            raise ApprovalTransitionError(
                f"Approval {approval_id} is not approved."
            )

        request = ExecutionRequest(
            tool_name=approval.tool_name,
            arguments=dict(arguments or {}),
            task_id=approval.task_id,
        )

        result = self.broker.execute(request)

        return ApprovalExecutionResult(
            status="executed" if result.success else "failed",
            approval_required=True,
            approval_id=approval_id,
            execution_result=result,
            error=result.error,
        )
