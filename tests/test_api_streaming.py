from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_analyze_stream_emits_workflow_events_and_verified_completion():
    fake_response = {
        "request_id": "test-request",
        "conversation_id": "test-conversation",
        "status": "completed",
        "final_answer": "Verified final answer",
        "evidence": [],
        "verification_status": "passed",
        "verification_results": [],
        "traceability": {},
        "execution_telemetry": {},
        "generated_deliverables": [],
        "stages": [
            {
                "stage_id": "task-test:understanding:1",
                "run_id": "task-test",
                "stage_type": "understanding",
                "status": "completed",
                "display_label": "Understanding request",
                "sequence": 1,
                "started_at": None,
                "completed_at": None,
                "metadata": {},
            }
        ],
        "execution_events": [
            {
                "event_id": "trace-1:1",
                "run_id": "task-test",
                "type": "run_started",
                "stage": None,
                "status": None,
                "sequence": 1,
                "timestamp": 1000.0,
                "metadata": {},
            }
        ],
    }

    with patch(
        "app.api.routes.run_multimodal_analysis",
        return_value=fake_response,
    ):
        response = client.post(
            "/analyze/stream",
            data={"user_query": "Test request"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text

    assert "event: workflow" in body
    assert "event: completed" in body
    assert "Verified final answer" in body
    assert "stages" in body
    assert "Understanding request" in body
    assert "execution_events" in body
    assert "run_started" in body


def test_analysis_status_recovers_result_from_durable_task_metadata():
    from types import SimpleNamespace

    from app.api import routes

    request_id = "recovery-request"

    durable_result = {
        "request_id": request_id,
        "task_id": "task-recovery",
        "conversation_id": "conversation-recovery",
        "status": "completed",
        "final_answer": "Recovered answer",
        "evidence": [],
        "verification_status": "passed",
        "verification_results": [],
        "stages": [],
        "execution_events": [],
        "generated_deliverables": [],
    }

    durable_task = SimpleNamespace(
        metadata={
            "request_id": request_id,
            "result": durable_result,
        }
    )

    class FakeStateManager:
        def find_task_by_metadata(self, key, value):
            assert key == "request_id"
            assert value == request_id
            return durable_task

    routes.analysis_store.clear()

    with patch.object(
        routes,
        "state_manager",
        FakeStateManager(),
    ):
        response = client.get(
            f"/analysis/{request_id}",
        )

    assert response.status_code == 200
    assert response.json() == {
        "request_id": request_id,
        "status": "completed",
        "verification_status": "passed",
        "final_answer": "Recovered answer",
        "generated_deliverables": [],
    }


def test_analysis_status_recovers_from_sqlite_task_state(tmp_path):
    from app.api import routes
    from app.state.manager import AgentStateManager
    from app.state.store import DurableStateStore

    request_id = "sqlite-recovery-request"
    task_id = "task-sqlite-recovery"

    store = DurableStateStore(
        database_path=tmp_path / "recovery.db",
    )
    manager = AgentStateManager(store=store)

    manager.create_task(
        task_id=task_id,
        goal="Recovery test",
    )

    manager.update_metadata(
        task_id,
        {
            "request_id": request_id,
            "result": {
                "request_id": request_id,
                "task_id": task_id,
                "conversation_id": "conversation-recovery",
                "status": "completed",
                "final_answer": "SQLite recovered answer",
                "evidence": [],
                "verification_status": "passed",
                "verification_results": [],
                "stages": [],
                "execution_events": [],
                "generated_deliverables": [],
            },
        },
    )

    routes.analysis_store.clear()

    with patch.object(
        routes,
        "state_manager",
        manager,
    ):
        response = client.get(
            f"/analysis/{request_id}",
        )

    assert response.status_code == 200
    assert response.json()["request_id"] == request_id
    assert response.json()["status"] == "completed"
    assert response.json()["final_answer"] == "SQLite recovered answer"


def test_stream_replays_durable_result_without_rerunning_workflow(tmp_path):
    from unittest.mock import patch
    from app.state.manager import AgentStateManager
    from app.state.store import DurableStateStore
    from app.state.models import AgentTaskState
    from app.api import routes

    store = DurableStateStore(tmp_path / "replay.db")
    manager = AgentStateManager(store=store)

    task_id = "task_replay_test"
    manager.create_task(
        task_id,
        "replay test",
    )

    manager.update_metadata(
        task_id,
        {
            "request_id": "req_replay_test",
            "result": {
                "request_id": "req_replay_test",
                "task_id": task_id,
                "conversation_id": "conv_replay_test",
                "status": "completed",
                "final_answer": "Recovered answer",
                "evidence": [],
                "verification_status": "passed",
                "verification_results": [],
                "stages": [],
                "execution_events": [],
                "generated_deliverables": [],
            },
        },
    )

    with patch.object(routes, "state_manager", manager), \
         patch.object(
             routes,
             "run_multimodal_analysis",
             side_effect=AssertionError(
                 "Workflow must not execute during replay"
             ),
         ):
        response = client.post(
            "/analyze/stream",
            data={
                "user_query": "should not execute",
                "task_id": task_id,
            },
        )

    assert response.status_code == 200
    body = response.text

    assert "event: workflow" in body
    assert "Analysis recovered" in body
    assert "event: completed" in body
    assert "Recovered answer" in body
    assert f'"run_id": "{task_id}"' in body
    assert f'"event_id": "{task_id}_3"' in body

    sequence_positions = [
        body.index(f'"sequence": {sequence}')
        for sequence in (1, 2, 3)
    ]
    assert sequence_positions == sorted(sequence_positions)




def test_stream_replays_durable_failure_without_rerunning_workflow(tmp_path):
    from unittest.mock import patch

    from app.api import routes
    from app.state.manager import AgentStateManager
    from app.state.store import DurableStateStore

    store = DurableStateStore(tmp_path / "failed_replay.db")
    manager = AgentStateManager(store=store)

    task_id = "task_failed_replay_test"

    manager.create_task(task_id, "failed replay test")
    manager.update_metadata(
        task_id,
        {
            "request_id": "req_failed_replay_test",
            "result": {
                "request_id": "req_failed_replay_test",
                "task_id": task_id,
                "conversation_id": "conv_failed_replay_test",
                "status": "failed",
                "final_answer": None,
                "evidence": [],
                "verification_status": None,
                "verification_results": [],
                "stages": [],
                "execution_events": [],
                "generated_deliverables": [],
                "error": {
                    "error_code": "ANALYSIS_EXECUTION_FAILED",
                    "classification": "RETRYABLE",
                    "user_message": "Analysis could not be completed.",
                    "retryable": True,
                    "recovery_action": "Retry the analysis.",
                    "run_id": task_id,
                    "stage": "ANALYZING",
                },
            },
        },
    )

    with (
        patch.object(routes, "state_manager", manager),
        patch.object(
            routes,
            "run_multimodal_analysis",
            side_effect=AssertionError(
                "Recovered failure must not rerun the workflow"
            ),
        ),
    ):
        response = client.post(
            "/analyze/stream",
            data={
                "user_query": "should not execute",
                "task_id": task_id,
            },
        )

    assert response.status_code == 200

    body = response.text

    assert "event: workflow" in body
    assert "Analysis recovered" in body
    assert "event: error" in body
    assert "event: completed" not in body
    assert "ANALYSIS_EXECUTION_FAILED" in body
    assert "Analysis could not be completed." in body
    assert f'"run_id": "{task_id}"' in body
    assert "should not execute" not in body

    sequence_positions = [
        body.index(f'"sequence": {sequence}')
        for sequence in (1, 2, 3)
    ]
    assert sequence_positions == sorted(sequence_positions)


def test_stream_reconnect_does_not_rerun_running_task(tmp_path):
    from unittest.mock import patch

    from app.api import routes
    from app.state.manager import AgentStateManager
    from app.state.store import DurableStateStore

    store = DurableStateStore(tmp_path / "running_reconnect.db")
    manager = AgentStateManager(store=store)

    task_id = "task_running_reconnect_test"

    manager.create_task(task_id, "running reconnect test")
    manager.start_task(task_id)

    with (
        patch.object(routes, "state_manager", manager),
        patch.object(
            routes,
            "run_multimodal_analysis",
            side_effect=AssertionError(
                "Reconnect must not rerun the workflow"
            ),
        ),
    ):
        response = client.post(
            "/analyze/stream",
            data={
                "user_query": "should not execute",
                "task_id": task_id,
            },
        )

    assert response.status_code == 200

    body = response.text

    assert "event: workflow" in body
    assert "Analysis state recovered" in body
    assert "Analysis is already in progress." in body
    assert '"run_id": "task_running_reconnect_test"' in body
    assert '"sequence": 1' in body
    assert '"sequence": 2' in body
    assert "should not execute" not in body

def test_analyze_persists_result_and_supports_optional_report():
    from unittest.mock import patch

    from app.api import routes
    from app.state.workflow_state import WorkflowState

    with patch.object(routes.WorkflowGraph, "build") as build_mock:
        workflow = build_mock.return_value

        def fake_invoke(state):
            return WorkflowState(
                request_id=state.request_id,
                task_id=state.task_id,
                conversation_id=state.conversation_id,
                user_query=state.user_query,
                final_answer="P13 integration result",
                verification_status="passed",
                verification_results=[],
                generated_deliverables=[],
                execution_events=[],
                execution_telemetry={},
                execution_trace=[],
            )

        workflow.invoke.side_effect = fake_invoke

        response = client.post(
            "/analyze",
            data={"user_query": "P13 integration test"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["task_id"].startswith("task_")
    assert body["final_answer"] == "P13 integration result"

    recovered = client.get(f"/analysis/{body['request_id']}")

    assert recovered.status_code == 200
    recovered_body = recovered.json()
    assert recovered_body["status"] == "completed"
    assert recovered_body["final_answer"] == "P13 integration result"

    report_response = client.post(
        f"/tasks/{body['task_id']}/reports",
        json={"title": "P13 Integration Report"},
    )

    assert report_response.status_code == 200
    report = report_response.json()
    assert report["task_id"] == body["task_id"]
    assert report["title"] == "P13 Integration Report"
    assert report["status"] == "completed"

    report_id = report["report_id"]
    fetched_report = client.get(f"/reports/{report_id}")

    assert fetched_report.status_code == 200
    assert fetched_report.json()["report_id"] == report_id
    assert fetched_report.json()["task_id"] == body["task_id"]


def test_run_analysis_failure_persists_durable_failure_result():
    from unittest.mock import patch

    from app.api import routes

    with patch.object(routes.WorkflowGraph, "build") as build_mock:
        workflow = build_mock.return_value
        workflow.invoke.side_effect = RuntimeError(
            "simulated workflow failure"
        )

        try:
            routes.run_multimodal_analysis(
                user_query="P13 failure integration test",
                files=[],
            )
            assert False, "Expected workflow failure"
        except RuntimeError:
            pass

    failed_tasks = [
        task
        for task in routes.state_manager.list_tasks()
        if task.status == "failed"
        and task.goal == "P13 failure integration test"
    ]

    assert failed_tasks

    task = failed_tasks[-1]
    request_id = task.metadata["request_id"]

    recovered = client.get(
        f"/analysis/{request_id}",
    )

    assert recovered.status_code == 200

    body = recovered.json()

    assert body["request_id"] == request_id
    assert body["status"] == "failed"
    assert body["verification_status"] is None
    assert body["final_answer"] is None
    assert body["generated_deliverables"] == []
