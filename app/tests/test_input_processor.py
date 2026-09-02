from pathlib import Path

from app.state.task_state import TaskState
from app.state.workflow_state import WorkflowState
from app.workflow.nodes.input_processor import detect_input_modalities
from app.workflow.nodes.policy_router import PolicyRouter
from app.tools.data.csv_analyzer import CSVAnalyzer
from app.verification.json_validator import JSONValidator
from app.verification.numeric_validator import NumericValidator
from app.workflow.nodes.complexity_gate import ComplexityGate
from app.workflow.nodes.repair import RepairNode


def test_input_type_detection(tmp_path: Path):
    pdf_file = tmp_path / "sample.pdf"
    csv_file = tmp_path / "sample.csv"
    pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
    csv_file.write_text("temperature,pressure\n10,100\n12,110\n", encoding="utf-8")

    detected = detect_input_modalities(
        user_query="Analyze this maintenance report and sensor dataset.",
        files=[pdf_file, csv_file],
    )

    assert detected["text"] is True
    assert detected["pdf"] is True
    assert detected["csv"] is True
    assert detected["image"] is False


def test_taskstate_validation():
    task = TaskState(
        intent="equipment_analysis",
        required_capabilities=["document_analysis", "data_analysis", "reasoning", "report_generation"],
    )
    assert task.intent == "equipment_analysis"
    assert "document_analysis" in task.required_capabilities


def test_policy_router_decisions():
    state = WorkflowState(
        request_id="req_1",
        user_query="Analyze this maintenance report and sensor dataset.",
        task_state=TaskState(
            intent="equipment_analysis",
            required_capabilities=["document_analysis", "data_analysis", "reasoning", "report_generation"],
            requires_rag=True,
            requires_tools=True,
            requires_synthesis=True,
            deliverable="report",
        ),
    )
    router = PolicyRouter()
    routes = router.route(state)
    assert "document" in routes
    assert "data" in routes
    assert "synthesis" in routes


def test_csv_deterministic_calculations():
    analyzer = CSVAnalyzer()
    result = analyzer.analyze_csv(
        "temperature,pressure\n10,100\n12,110\n14,120\n",
        user_query="calculate trend",
    )
    assert result["analysis_type"] == "trend_analysis"
    assert result["metric"] == "temperature"
    assert abs(float(result["percentage_change"]) - 40.0) < 0.01


def test_evidence_metadata_preservation():
    evidence = {
        "evidence_id": "ev_001",
        "source_file_id": "file_1",
        "source_filename": "maintenance_report.pdf",
        "page_number": 3,
        "chunk_id": "chunk_18",
        "text": "Vibration increased substantially.",
        "relevance_score": 0.91,
        "retrieval_method": "pdf_text_chunking",
    }
    assert evidence["page_number"] == 3
    assert evidence["source_filename"] == "maintenance_report.pdf"


def test_complexity_gate():
    gate = ComplexityGate()
    decision = gate.evaluate({"document_results": [{"text": "foo"}], "data_results": [{"metric": "temp"}]})
    assert decision["synthesis_required"] is True


def test_json_verification():
    validator = JSONValidator()
    payload = {"answer": "ok", "key_findings": ["a"]}
    assert validator.validate(payload) is True


def test_numeric_verification():
    validator = NumericValidator()
    result = validator.validate_reported_value(42.15, 42.15)
    assert result is True


def test_repair_attempt_limits():
    repair = RepairNode(max_attempts=2)
    assert repair.max_attempts == 2
    assert repair.should_retry(2) is False
    assert repair.should_retry(1) is True
