
import pytest

from app.services.run_trace import RunTrace


def test_run_trace_preserves_ordered_run_and_step_events():
    trace = RunTrace()

    trace_id = trace.start_run("task-1", "plan-1")

    trace.record_step_started(
        trace_id,
        "step-1",
        "CSVAnalyzer",
    )
    trace.record_step_completed(
        trace_id,
        "step-1",
        "CSVAnalyzer",
        duration_ms=12.5,
    )

    trace.finish_run(trace_id, "completed")

    events = trace.get_events(trace_id)

    assert [event.event_type for event in events] == [
        "run_started",
        "step_started",
        "step_completed",
        "run_completed",
    ]

    assert [event.sequence for event in events] == [1, 2, 3, 4]
    assert all(event.trace_id == trace_id for event in events)
    assert all(event.task_id == "task-1" for event in events)


def test_run_trace_records_step_failure():
    trace = RunTrace()
    trace_id = trace.start_run("task-2", "plan-2")

    trace.record_step_started(
        trace_id,
        "step-1",
        "CodeSandbox",
    )
    trace.record_step_failed(
        trace_id,
        "step-1",
        "CodeSandbox",
        error="sandbox failed",
        duration_ms=5.0,
    )
    trace.finish_run(trace_id, "failed")

    events = trace.get_events(trace_id)

    failed = events[2]

    assert failed.event_type == "step_failed"
    assert failed.status == "failed"
    assert failed.error == "sandbox failed"
    assert failed.duration_ms == 5.0

    run = trace.get_run(trace_id)

    assert run.status == "failed"
    assert run.completed_at_ms is not None


def test_run_trace_snapshot_is_serializable():
    trace = RunTrace()
    trace_id = trace.start_run(
        "task-3",
        "plan-3",
    )

    trace.record_step_skipped(
        trace_id,
        "step-2",
        "CSVAnalyzer",
        metadata={"reason": "dependency_failed"},
    )

    snapshot = trace.snapshot(trace_id)

    assert snapshot["trace_id"] == trace_id
    assert snapshot["task_id"] == "task-3"
    assert snapshot["plan_id"] == "plan-3"
    assert snapshot["events"][1]["event_type"] == "step_skipped"
    assert snapshot["events"][1]["metadata"]["reason"] == "dependency_failed"


def test_unknown_trace_is_rejected():
    trace = RunTrace()

    with pytest.raises(KeyError):
        trace.get_events("missing")
