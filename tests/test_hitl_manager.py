from datetime import datetime, timedelta, timezone

import pytest

from app.hitl.manager import (
    ApprovalManager,
    ApprovalNotFoundError,
    ApprovalTransitionError,
)
from app.hitl.models import ApprovalStatus


def create_manager_request(manager: ApprovalManager, **kwargs):
    return manager.create_request(
        task_id="task-1",
        step_id="step-1",
        tool_name="ToolA",
        reason="approval required",
        risk_level="high",
        requested_action="run ToolA",
        requested_arguments_summary="safe summary",
        **kwargs,
    )


def test_create_and_get_pending_request():
    manager = ApprovalManager()

    request = create_manager_request(manager)

    assert request.status is ApprovalStatus.PENDING
    assert manager.get_request(request.approval_id).status is ApprovalStatus.PENDING


def test_approve_pending_request():
    manager = ApprovalManager()
    request = create_manager_request(manager)

    approved = manager.approve(request.approval_id)

    assert approved.status is ApprovalStatus.APPROVED


def test_reject_pending_request():
    manager = ApprovalManager()
    request = create_manager_request(manager)

    rejected = manager.reject(request.approval_id)

    assert rejected.status is ApprovalStatus.REJECTED


def test_cancel_pending_request():
    manager = ApprovalManager()
    request = create_manager_request(manager)

    cancelled = manager.cancel(request.approval_id)

    assert cancelled.status is ApprovalStatus.CANCELLED


def test_expire_pending_request():
    manager = ApprovalManager()

    expired_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()

    request = create_manager_request(
        manager,
        created_at=(datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
        expires_at=expired_at,
    )

    loaded = manager.get_request(request.approval_id)

    assert loaded.status is ApprovalStatus.EXPIRED


def test_expired_request_cannot_be_approved():
    manager = ApprovalManager()

    expires_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()

    request = create_manager_request(
        manager,
        created_at=(datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
        expires_at=expires_at,
    )

    with pytest.raises(ApprovalTransitionError):
        manager.approve(request.approval_id)


def test_approved_request_cannot_be_approved_again():
    manager = ApprovalManager()
    request = create_manager_request(manager)

    manager.approve(request.approval_id)

    with pytest.raises(ApprovalTransitionError):
        manager.approve(request.approval_id)


def test_rejected_request_cannot_be_cancelled():
    manager = ApprovalManager()
    request = create_manager_request(manager)

    manager.reject(request.approval_id)

    with pytest.raises(ApprovalTransitionError):
        manager.cancel(request.approval_id)


def test_unknown_request_raises():
    manager = ApprovalManager()

    with pytest.raises(ApprovalNotFoundError):
        manager.get_request("missing")


def test_list_pending_filters_by_task(tmp_path):
    manager = ApprovalManager(database_path=tmp_path / "approvals.db")

    first = create_manager_request(manager)
    second = manager.create_request(
        task_id="task-2",
        step_id="step-2",
        tool_name="ToolB",
        reason="approval required",
        risk_level="high",
        requested_action="run ToolB",
        requested_arguments_summary="safe summary",
    )

    manager.approve(first.approval_id)

    pending = manager.list_pending(task_id="task-2")

    assert [item.approval_id for item in pending] == [second.approval_id]


def test_explicit_expire_is_idempotent():
    manager = ApprovalManager()
    request = create_manager_request(manager)

    expired = manager.expire(request.approval_id)
    expired_again = manager.expire(request.approval_id)

    assert expired.status is ApprovalStatus.EXPIRED
    assert expired_again.status is ApprovalStatus.EXPIRED

def test_approval_survives_manager_restart(tmp_path):
    database_path = tmp_path / "approval_state.db"

    manager_one = ApprovalManager(
        database_path=str(database_path),
    )

    request = create_manager_request(manager_one)

    manager_two = ApprovalManager(
        database_path=str(database_path),
    )

    loaded = manager_two.get_request(request.approval_id)

    assert loaded.approval_id == request.approval_id
    assert loaded.task_id == request.task_id
    assert loaded.step_id == request.step_id
    assert loaded.tool_name == request.tool_name
    assert loaded.status is ApprovalStatus.PENDING


def test_approval_status_survives_manager_restart(tmp_path):
    database_path = tmp_path / "approval_state.db"

    manager_one = ApprovalManager(
        database_path=str(database_path),
    )

    request = create_manager_request(manager_one)
    manager_one.approve(request.approval_id)

    manager_two = ApprovalManager(
        database_path=str(database_path),
    )

    loaded = manager_two.get_request(request.approval_id)

    assert loaded.status is ApprovalStatus.APPROVED


def test_pending_approvals_survive_manager_restart(tmp_path):
    database_path = tmp_path / "approval_state.db"

    manager_one = ApprovalManager(
        database_path=str(database_path),
    )

    request = create_manager_request(manager_one)

    manager_two = ApprovalManager(
        database_path=str(database_path),
    )

    pending = manager_two.list_pending(
        task_id=request.task_id,
    )

    assert [item.approval_id for item in pending] == [
        request.approval_id
    ]
