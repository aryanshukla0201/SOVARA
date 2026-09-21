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
