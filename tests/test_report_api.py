from fastapi.testclient import TestClient

from app.main import app
from app.api import routes
from app.report.store import ReportStore
from app.state.manager import AgentStateManager
from app.state.store import DurableStateStore


client = TestClient(app)


def _build_completed_task(tmp_path):
    store = DurableStateStore(
        database_path=tmp_path / "report_task.db",
    )
    manager = AgentStateManager(store=store)

    task_id = "task-report-test"

    manager.create_task(
        task_id=task_id,
        goal="Generate a report",
    )

    manager.start_task(task_id)

    manager.update_metadata(
        task_id,
        {
            "request_id": "request-report-test",
            "run_id": task_id,
            "result": {
                "request_id": "request-report-test",
                "task_id": task_id,
                "status": "completed",
                "final_answer": "Verified report answer",
                "evidence": [
                    {
                        "evidence_id": "ev-1",
                        "source_file_id": "file-1",
                        "source_filename": "source.txt",
                        "page_number": 3,
                        "citation_id": "cite-1",
                        "text": "Important evidence",
                    }
                ],
                "verification_status": "passed",
                "verification_results": [
                    {
                        "status": "verified",
                        "message": "Result verified",
                    }
                ],
                "generated_deliverables": [],
            },
        },
    )

    manager.complete_task(task_id)

    return manager, task_id


def test_create_report_from_completed_task(tmp_path):
    manager, task_id = _build_completed_task(tmp_path)

    report_store = ReportStore(
        database_path=tmp_path / "reports.db",
    )

    original_state_manager = routes.state_manager
    original_report_service = routes.report_service

    from app.report.service import ReportService

    routes.state_manager = manager
    routes.report_service = ReportService(
        state_manager=manager,
        store=report_store,
    )

    try:
        response = client.post(
            f"/tasks/{task_id}/reports",
            json={
                "title": "Test Report",
                "subtitle": "Generated from task result",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["task_id"] == task_id
        assert body["title"] == "Test Report"
        assert body["status"] == "completed"
        assert body["summary"] == "Verified report answer"
        assert body["verification"]["status"] == "passed"
        assert body["evidence"][0]["evidence_id"] == "ev-1"

    finally:
        routes.state_manager = original_state_manager
        routes.report_service = original_report_service


def test_get_report_returns_persisted_report(tmp_path):
    manager, task_id = _build_completed_task(tmp_path)

    report_store = ReportStore(
        database_path=tmp_path / "reports.db",
    )

    from app.report.service import ReportService

    service = ReportService(
        state_manager=manager,
        store=report_store,
    )

    report = service.create_report(
        task_id=task_id,
        title="Persisted Report",
    )

    original_service = routes.report_service
    routes.report_service = service

    try:
        response = client.get(
            f"/reports/{report.report_id}",
        )

        assert response.status_code == 200
        assert response.json()["report_id"] == report.report_id
        assert response.json()["title"] == "Persisted Report"

    finally:
        routes.report_service = original_service


def test_list_reports_for_task(tmp_path):
    manager, task_id = _build_completed_task(tmp_path)

    report_store = ReportStore(
        database_path=tmp_path / "reports.db",
    )

    from app.report.service import ReportService

    service = ReportService(
        state_manager=manager,
        store=report_store,
    )

    report = service.create_report(
        task_id=task_id,
        title="List Test Report",
    )

    original_service = routes.report_service
    routes.report_service = service

    try:
        response = client.get(
            f"/tasks/{task_id}/reports",
        )

        assert response.status_code == 200

        body = response.json()

        assert body["task_id"] == task_id
        assert len(body["reports"]) == 1
        assert body["reports"][0]["report_id"] == report.report_id

    finally:
        routes.report_service = original_service


def test_report_generation_rejects_incomplete_task(tmp_path):
    store = DurableStateStore(
        database_path=tmp_path / "incomplete.db",
    )
    manager = AgentStateManager(store=store)

    task_id = "task-incomplete-report"

    manager.create_task(
        task_id=task_id,
        goal="Incomplete task",
    )

    report_store = ReportStore(
        database_path=tmp_path / "reports.db",
    )

    from app.report.service import ReportService

    original_service = routes.report_service
    routes.report_service = ReportService(
        state_manager=manager,
        store=report_store,
    )

    try:
        response = client.post(
            f"/tasks/{task_id}/reports",
            json={},
        )

        assert response.status_code == 409
        assert "completed task" in response.json()["detail"]

    finally:
        routes.report_service = original_service


def test_missing_report_returns_404():
    response = client.get(
        "/reports/nonexistent-report",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found."