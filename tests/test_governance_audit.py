from app.governance.audit import AuditEvent, AuditEventType


def test_audit_event_create():
    event = AuditEvent.create(
        event_id="evt-1",
        task_id="task-1",
        event_type=AuditEventType.POLICY_ALLOWED,
        tool_name="CSVAnalyzer",
        action="execute",
        decision="allow",
        reason="tool permitted by policy",
        metadata={"risk": "low"},
    )

    assert event.event_id == "evt-1"
    assert event.task_id == "task-1"
    assert event.event_type == "policy_allowed"
    assert event.tool_name == "CSVAnalyzer"
    assert event.decision == "allow"
    assert event.metadata == {"risk": "low"}
    assert event.timestamp


def test_audit_event_serialization_round_trip():
    event = AuditEvent(
        event_id="evt-2",
        task_id="task-2",
        timestamp="2026-09-21T12:00:00+00:00",
        event_type=AuditEventType.EXECUTION_COMPLETED,
        tool_name="CSVAnalyzer",
        action="execute",
        decision="allow",
        reason="execution completed",
        metadata={"rows": 10},
    )

    data = event.to_dict()

    assert data == {
        "event_id": "evt-2",
        "task_id": "task-2",
        "timestamp": "2026-09-21T12:00:00+00:00",
        "event_type": "execution_completed",
        "tool_name": "CSVAnalyzer",
        "action": "execute",
        "decision": "allow",
        "reason": "execution completed",
        "metadata": {"rows": 10},
    }

    restored = AuditEvent.from_dict(data)

    assert restored == event


def test_audit_event_supports_minimal_event():
    event = AuditEvent(
        event_id="evt-3",
        task_id="task-3",
        timestamp="2026-09-21T12:00:00+00:00",
        event_type=AuditEventType.TASK_CREATED,
    )

    assert event.to_dict()["metadata"] == {}
    assert event.tool_name == ""
    assert event.action == ""
    assert event.decision == ""
    assert event.reason == ""
