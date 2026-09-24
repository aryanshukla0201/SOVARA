from app.report.composer import ReportComposer
from app.state.result_state import ResultState
from app.state.evidence import EvidenceRecord


def test_composer_builds_summary_evidence_and_verification():
    result = ResultState(
        final_answer="Verified final answer",
        verification_status="passed",
        verification_results=[
            {
                "status": "verified",
                "message": "Result verified",
            }
        ],
        retrieved_evidence=[
            EvidenceRecord(
                evidence_id="ev-1",
                source_file_id="file-1",
                source_filename="source.txt",
                document_id="doc-1",
                page_number=4,
                citation_id="cite-1",
                text="Important evidence",
            )
        ],
    )

    report = ReportComposer().compose(
        task_id="task-1",
        result=result,
        title="Test Report",
        subtitle="Composer Test",
    )

    assert report.task_id == "task-1"
    assert report.title == "Test Report"
    assert report.subtitle == "Composer Test"
    assert report.status.value == "completed"
    assert report.summary == "Verified final answer"

    assert len(report.evidence) == 1
    assert report.evidence[0].evidence_id == "ev-1"
    assert report.evidence[0].source_file_id == "file-1"
    assert report.evidence[0].page_number == 4
    assert report.evidence[0].citation_id == "cite-1"

    assert report.verification.status == "passed"
    assert report.verification.results[0]["status"] == "verified"


def test_composer_builds_structured_findings():
    result = ResultState(
        final_answer="Analysis complete",
        aggregated_results={
            "findings": [
                {
                    "finding_id": "finding-1",
                    "finding_type": "observation",
                    "severity": "medium",
                    "title": "Observed issue",
                    "body": "An issue was identified.",
                    "evidence_ids": ["ev-1"],
                    "verification_status": "verified",
                }
            ]
        },
    )

    report = ReportComposer().compose(
        task_id="task-findings",
        result=result,
    )

    assert len(report.findings) == 1

    finding = report.findings[0]

    assert finding.finding_id == "finding-1"
    assert finding.finding_type == "observation"
    assert finding.severity == "medium"
    assert finding.title == "Observed issue"
    assert finding.body == "An issue was identified."
    assert finding.evidence_ids == ["ev-1"]
    assert finding.verification_status == "verified"

    findings_section = next(
        section
        for section in report.sections
        if section.section_id == "findings"
    )

    assert len(findings_section.blocks) == 1
    assert findings_section.blocks[0].block_type == "finding"


def test_composer_maps_generated_deliverables_to_artifacts():
    result = ResultState(
        final_answer="Completed",
        generated_deliverables=[
            "analysis.csv",
            "summary.pdf",
        ],
    )

    report = ReportComposer().compose(
        task_id="task-artifacts",
        result=result,
    )

    assert len(report.artifacts) == 2
    assert report.artifacts[0].artifact_id == "analysis.csv"
    assert report.artifacts[0].name == "analysis.csv"
    assert report.artifacts[1].artifact_id == "summary.pdf"


def test_composer_serializes_to_json():
    result = ResultState(
        final_answer="Serializable report",
        verification_status="passed",
    )

    report = ReportComposer().compose(
        task_id="task-json",
        result=result,
    )

    payload = report.model_dump(mode="json")

    assert isinstance(payload, dict)
    assert payload["task_id"] == "task-json"
    assert payload["status"] == "completed"
    assert isinstance(payload["sections"], list)
    assert isinstance(payload["findings"], list)
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["verification"], dict)
    assert isinstance(payload["artifacts"], list)
