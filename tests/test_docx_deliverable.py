from pathlib import Path
from types import SimpleNamespace

from app.state.workflow_state import WorkflowState
from app.workflow.graph import WorkflowGraph


def test_deliverable_accepts_docx_format(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "outputs").mkdir()

    state = WorkflowState(
        request_id="req_docx_test",
        user_query="Generate a report",
        requested_deliverable="docx",
        final_answer="Verified report answer",
        verification_status="passed",
        verification_results=[
            {
                "verification_status": "passed",
                "failures": [],
                "numeric_validation": [],
            }
        ],
    )

    graph = WorkflowGraph.__new__(WorkflowGraph)
    graph.telemetry = SimpleNamespace(
        summary=lambda: {}
    )

    result = graph._deliverable(state)

    assert len(result.generated_deliverables) == 1
    assert Path(result.generated_deliverables[0]) == Path(
        "outputs/req_docx_test_report.docx"
    )

    output_file = Path("outputs/req_docx_test_report.docx")

    assert output_file.exists()
    assert output_file.stat().st_size > 0
    assert output_file.read_bytes()[:4] == b"PK\x03\x04"
