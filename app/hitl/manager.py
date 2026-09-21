from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.hitl.models import ApprovalRequest, ApprovalStatus
from app.hitl.store import ApprovalStore


class ApprovalTransitionError(ValueError):
    """Raised when an approval status transition is invalid."""


class ApprovalNotFoundError(KeyError):
    """Raised when an approval request does not exist."""


class ApprovalManager:
    def __init__(
        self,
        store: ApprovalStore | None = None,
        *,
        database_path: str = "data/sovara_state.db",
    ) -> None:
        self.store = store or ApprovalStore(database_path)
        self._lock = RLock()

    def create_request(
        self,
        *,
        task_id: str,
        step_id: str,
        tool_name: str,
        reason: str,
        risk_level: str,
        requested_action: str,
        requested_arguments_summary: str,
        created_at: str | None = None,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
        approval_id: str | None = None,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            approval_id=approval_id or uuid4().hex,
            task_id=task_id,
            step_id=step_id,
            tool_name=tool_name,
            reason=reason,
            risk_level=risk_level,
            requested_action=requested_action,
            requested_arguments_summary=requested_arguments_summary,
            created_at=created_at or self._now(),
            expires_at=expires_at,
            metadata=dict(metadata or {}),
        )

        with self._lock:
            if self.store.get(request.approval_id) is not None:
                raise ValueError(
                    f"Approval request already exists: "
                    f"{request.approval_id}"
                )

            return self.store.save(request)

    def get_request(self, approval_id: str) -> ApprovalRequest:
        with self._lock:
            request = self._get(approval_id)
            request = self._expire_if_needed(request)
            return request

    def approve(self, approval_id: str) -> ApprovalRequest:
        return self._transition(
            approval_id,
            ApprovalStatus.APPROVED,
        )

    def reject(self, approval_id: str) -> ApprovalRequest:
        return self._transition(
            approval_id,
            ApprovalStatus.REJECTED,
        )

    def cancel(self, approval_id: str) -> ApprovalRequest:
        return self._transition(
            approval_id,
            ApprovalStatus.CANCELLED,
        )

    def expire(self, approval_id: str) -> ApprovalRequest:
        with self._lock:
            request = self._get(approval_id)

            if request.status is ApprovalStatus.EXPIRED:
                return request

            if request.status is not ApprovalStatus.PENDING:
                raise ApprovalTransitionError(
                    f"Cannot expire approval in status: "
                    f"{request.status.value}"
                )

            updated = self._replace_status(
                request,
                ApprovalStatus.EXPIRED,
            )
            return self.store.save(updated)

    def list_pending(
        self,
        *,
        task_id: str | None = None,
    ) -> list[ApprovalRequest]:
        with self._lock:
            requests = self.store.list_pending(task_id)

            pending: list[ApprovalRequest] = []

            for request in requests:
                request = self._expire_if_needed(request)

                if request.status is ApprovalStatus.PENDING:
                    pending.append(request)

            return pending

    def _transition(
        self,
        approval_id: str,
        target: ApprovalStatus,
    ) -> ApprovalRequest:
        with self._lock:
            request = self._get(approval_id)
            request = self._expire_if_needed(request)

            if request.status is not ApprovalStatus.PENDING:
                raise ApprovalTransitionError(
                    f"Cannot transition approval from "
                    f"{request.status.value} to {target.value}"
                )

            updated = self._replace_status(request, target)
            return self.store.save(updated)

    def _get(self, approval_id: str) -> ApprovalRequest:
        request = self.store.get(approval_id)

        if request is None:
            raise ApprovalNotFoundError(
                f"Approval request not found: {approval_id}"
            )

        return request

    def _expire_if_needed(
        self,
        request: ApprovalRequest,
    ) -> ApprovalRequest:
        if request.status is not ApprovalStatus.PENDING:
            return request

        if not request.expires_at:
            return request

        expires_at = self._parse_timestamp(request.expires_at)

        if self._parse_timestamp(request.created_at) <= expires_at <= self._now_dt():
            expired = self._replace_status(
                request,
                ApprovalStatus.EXPIRED,
            )
            return self.store.save(expired)

        return request

    @staticmethod
    def _replace_status(
        request: ApprovalRequest,
        status: ApprovalStatus,
    ) -> ApprovalRequest:
        return ApprovalRequest(
            approval_id=request.approval_id,
            task_id=request.task_id,
            step_id=request.step_id,
            tool_name=request.tool_name,
            reason=request.reason,
            risk_level=request.risk_level,
            requested_action=request.requested_action,
            requested_arguments_summary=request.requested_arguments_summary,
            created_at=request.created_at,
            expires_at=request.expires_at,
            status=status,
            metadata=dict(request.metadata),
        )

    @staticmethod
    def _now() -> str:
        return ApprovalManager._now_dt().isoformat()

    @staticmethod
    def _now_dt() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)
