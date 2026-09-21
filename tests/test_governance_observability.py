from app.governance.audit import AuditEvent, AuditEventType
from app.governance.observability import Observability


def make_event(event_id: str, task_id: str, event_type: str) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        task_id=task_id,
        timestamp="2026-09-21T12:00:00+00:00",
        event_type=event_type,
    )


def test_record_and_get_events_by_task():
    observability = Observability()

    event_one = make_event(
        "evt-1",
        "task-1",
        AuditEventType.EXECUTION_STARTED,
    )
    event_two = make_event(
        "evt-2",
        "task-2",
        AuditEventType.EXECUTION_COMPLETED,
    )

    observability.record(event_one)
    observability.record(event_two)

    assert observability.get_events("task-1") == [event_one]
    assert observability.get_events("task-2") == [event_two]


def test_events_preserve_recording_order():
    observability = Observability()

    first = make_event("evt-1", "task-1", AuditEventType.POLICY_ALLOWED)
    second = make_event(
        "evt-2",
        "task-1",
        AuditEventType.EXECUTION_STARTED,
    )

    observability.record(first)
    observability.record(second)

    assert observability.get_events("task-1") == [first, second]


def test_clear_removes_all_events():
    observability = Observability()

    observability.record(
        make_event("evt-1", "task-1", AuditEventType.TASK_CREATED)
    )

    observability.clear()

    assert observability.get_events("task-1") == []


def test_metrics_count_execution_and_policy_events():
    observability = Observability()

    observability.record(
        make_event("evt-1", "task-1", AuditEventType.EXECUTION_STARTED)
    )
    observability.record(
        make_event("evt-2", "task-1", AuditEventType.EXECUTION_COMPLETED)
    )
    observability.record(
        make_event("evt-3", "task-1", AuditEventType.EXECUTION_STARTED)
    )
    observability.record(
        make_event("evt-4", "task-1", AuditEventType.EXECUTION_FAILED)
    )
    observability.record(
        make_event("evt-5", "task-1", AuditEventType.POLICY_DENIED)
    )

    assert observability.metrics() == {
        "execution_started": 2,
        "execution_completed": 1,
        "execution_failed": 1,
        "policy_denied": 1,
        "tool_invocation_count": 2,
    }


def test_metrics_are_zero_when_empty():
    observability = Observability()

    assert observability.metrics() == {
        "execution_started": 0,
        "execution_completed": 0,
        "execution_failed": 0,
        "policy_denied": 0,
        "tool_invocation_count": 0,
    }
