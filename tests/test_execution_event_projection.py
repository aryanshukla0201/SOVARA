from app.services.run_trace import RunTrace
from app.state.execution_event_projection import (
    project_run_trace_events,
)


def test_projection_exposes_only_user_safe_run_events():
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

    events = project_run_trace_events(
        trace.get_events(trace_id),
    )

    assert [event.type for event in events] == [
        "run_started",
        "step_started",
        "step_completed",
        "run_completed",
    ]

    assert [event.sequence for event in events] == [1, 2, 3, 4]
    assert all(event.run_id == "task-1" for event in events)
    assert all(event.event_id for event in events)

    assert not hasattr(events[1], "tool_name")
    assert not hasattr(events[1], "error")


def test_projection_maps_failed_event_without_exposing_raw_error():
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
        error="secret internal failure",
    )
    trace.finish_run(trace_id, "failed")

    events = project_run_trace_events(
        trace.get_events(trace_id),
    )

    failed = events[2]

    assert failed.type == "step_failed"
    assert failed.status == "failed"
    assert failed.run_id == "task-2"
    assert "secret internal failure" not in str(failed)
    assert "CodeSandbox" not in str(failed)


def test_projection_preserves_safe_metadata_only():
    trace = RunTrace()
    trace_id = trace.start_run("task-3")

    trace.record_step_skipped(
        trace_id,
        "step-2",
        "CSVAnalyzer",
        metadata={
            "reason": "dependency_failed",
            "safe_label": "Previous step failed",
        },
    )

    events = project_run_trace_events(
        trace.get_events(trace_id),
    )

    skipped = events[1]

    assert skipped.type == "step_skipped"
    assert skipped.status == "skipped"
    assert skipped.metadata == {
        "reason": "dependency_failed",
        "safe_label": "Previous step failed",
    }
