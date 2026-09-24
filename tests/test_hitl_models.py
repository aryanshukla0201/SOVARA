from app.hitl.models import ApprovalRequest, ApprovalStatus


def test_approval_status_values():
    assert ApprovalStatus.PENDING.value == "pending"
    assert ApprovalStatus.APPROVED.value == "approved"
    assert ApprovalStatus.REJECTED.value == "rejected"
    assert ApprovalStatus.EXPIRED.value == "expired"
    assert ApprovalStatus.CANCELLED.value == "cancelled"


def test_approval_request_defaults_to_pending():
    request = ApprovalRequest(
        approval_id="approval-1",
        task_id="task-1",
        step_id="step-1",
        tool_name="DeleteFile",
        reason="Destructive action requires human approval",
        risk_level="high",
        requested_action="Delete selected file",
        requested_arguments_summary="path=<redacted>",
        created_at="2026-09-21T10:00:00+00:00",
    )

    assert request.status is ApprovalStatus.PENDING
    assert request.expires_at is None
    assert request.metadata == {}


def test_approval_request_serialization_round_trip():
    request = ApprovalRequest(
        approval_id="approval-1",
        task_id="task-1",
        step_id="step-1",
        tool_name="DeleteFile",
        reason="Destructive action requires human approval",
        risk_level="high",
        requested_action="Delete selected file",
        requested_arguments_summary="path=<redacted>",
        created_at="2026-09-21T10:00:00+00:00",
        expires_at="2026-09-21T11:00:00+00:00",
        metadata={"source": "policy"},
    )

    restored = ApprovalRequest.from_dict(request.to_dict())

    assert restored == request
    assert restored.status is ApprovalStatus.PENDING


def test_approval_request_serializes_status_as_string():
    request = ApprovalRequest(
        approval_id="approval-1",
        task_id="task-1",
        step_id="step-1",
        tool_name="ToolA",
        reason="approval required",
        risk_level="medium",
        requested_action="run action",
        requested_arguments_summary="safe summary",
        created_at="2026-09-21T10:00:00+00:00",
        status=ApprovalStatus.REJECTED,
    )

    payload = request.to_dict()

    assert payload["status"] == "rejected"


def test_approval_request_rejects_missing_identity_fields():
    try:
        ApprovalRequest(
            approval_id="",
            task_id="task-1",
            step_id="step-1",
            tool_name="ToolA",
            reason="approval required",
            risk_level="medium",
            requested_action="run action",
            requested_arguments_summary="safe summary",
            created_at="2026-09-21T10:00:00+00:00",
        )
    except ValueError as exc:
        assert "approval_id" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
