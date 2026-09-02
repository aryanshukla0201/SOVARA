from __future__ import annotations

from app.verification.citation_validator import CitationValidator
from app.verification.numeric_validator import NumericValidator
from app.verification.report_validator import ReportValidator


class Verifier:
    def __init__(self):
        self.numeric_validator = NumericValidator()
        self.citation_validator = CitationValidator()
        self.report_validator = ReportValidator()

    def verify(self, answer: str, evidence: list[dict], report: dict | None = None) -> dict:
        evidence_ids = [item.get("evidence_id") for item in evidence if isinstance(item, dict)]
        status = "passed"
        failures = []
        if not self.citation_validator.validate(answer, evidence_ids):
            failures.append("citation_validation_failed")
            status = "failed"
        if report and not self.report_validator.validate(report):
            failures.append("report_structure_invalid")
            status = "failed"
        return {"verification_status": status, "failures": failures}
