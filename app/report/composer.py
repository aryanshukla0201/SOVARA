from __future__ import annotations

from uuid import uuid4

from app.report.models import (
    ArtifactReference,
    EvidenceReference,
    Report,
    ReportBlock,
    ReportFinding,
    ReportSection,
    ReportStatus,
    VerificationSummary,
)
from app.state.evidence import EvidenceRecord
from app.state.result_state import ResultState


class ReportComposer:
    """Transform an existing task result into a structured report."""

    def compose(
        self,
        *,
        task_id: str,
        result: ResultState,
        title: str | None = None,
        subtitle: str | None = None,
        run_id: str | None = None,
        project_id: str | None = None,
    ) -> Report:
        if not task_id.strip():
            raise ValueError("task_id must not be empty")

        report_title = (
            title.strip()
            if title and title.strip()
            else "SOVARA Task Report"
        )

        evidence = [
            self._evidence_reference(item)
            for item in result.retrieved_evidence
        ]

        findings = self._build_findings(result)

        sections = self._build_sections(
            result=result,
            findings=findings,
        )

        verification = VerificationSummary(
            status=result.verification_status,
            results=list(result.verification_results),
        )

        artifacts = [
            ArtifactReference(
                artifact_id=artifact,
                name=artifact,
            )
            for artifact in result.generated_deliverables
        ]

        summary = result.final_answer or result.direct_output

        return Report(
            report_id=f"report-{uuid4().hex}",
            task_id=task_id,
            run_id=run_id,
            project_id=project_id,
            title=report_title,
            subtitle=subtitle,
            status=ReportStatus.COMPLETED,
            summary=summary,
            sections=sections,
            findings=findings,
            evidence=evidence,
            verification=verification,
            artifacts=artifacts,
        )

    @staticmethod
    def _evidence_reference(
        evidence: EvidenceRecord,
    ) -> EvidenceReference:
        return EvidenceReference(
            evidence_id=evidence.evidence_id,
            source_file_id=evidence.source_file_id,
            source_filename=evidence.source_filename,
            document_id=evidence.document_id,
            page_number=evidence.page_number,
            citation_id=evidence.citation_id,
        )

    @staticmethod
    def _build_findings(
        result: ResultState,
    ) -> list[ReportFinding]:
        findings: list[ReportFinding] = []

        for index, item in enumerate(result.aggregated_results.get(
            "findings",
            [],
        )):
            if not isinstance(item, dict):
                continue

            finding_id = str(
                item.get("finding_id")
                or f"finding-{index + 1}"
            )

            findings.append(
                ReportFinding(
                    finding_id=finding_id,
                    finding_type=str(
                        item.get("finding_type")
                        or item.get("type")
                        or "finding"
                    ),
                    severity=item.get("severity"),
                    title=str(
                        item.get("title")
                        or f"Finding {index + 1}"
                    ),
                    body=str(
                        item.get("body")
                        or item.get("description")
                        or ""
                    ),
                    evidence_ids=[
                        str(value)
                        for value in item.get("evidence_ids", [])
                    ],
                    verification_status=str(
                        item.get(
                            "verification_status",
                            result.verification_status,
                        )
                    ),
                )
            )

        return findings

    @staticmethod
    def _build_sections(
        *,
        result: ResultState,
        findings: list[ReportFinding],
    ) -> list[ReportSection]:
        sections: list[ReportSection] = []

        summary = result.final_answer or result.direct_output

        if summary:
            sections.append(
                ReportSection(
                    section_id="summary",
                    title="Summary",
                    blocks=[
                        ReportBlock(
                            block_id="summary-text",
                            block_type="paragraph",
                            content={"text": summary},
                        )
                    ],
                )
            )

        if findings:
            sections.append(
                ReportSection(
                    section_id="findings",
                    title="Findings",
                    blocks=[
                        ReportBlock(
                            block_id=finding.finding_id,
                            block_type="finding",
                            content=finding.model_dump(
                                mode="json"
                            ),
                        )
                        for finding in findings
                    ],
                )
            )

        if result.verification_results:
            sections.append(
                ReportSection(
                    section_id="verification",
                    title="Verification",
                    blocks=[
                        ReportBlock(
                            block_id="verification-summary",
                            block_type="verification",
                            content={
                                "status": result.verification_status,
                                "results": list(
                                    result.verification_results
                                ),
                            },
                        )
                    ],
                )
            )

        return sections
