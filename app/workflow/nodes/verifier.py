from __future__ import annotations

from app.verification.citation_validator import CitationValidator
from app.verification.numeric_validator import NumericValidator
from app.verification.report_validator import ReportValidator


class Verifier:
    def __init__(self):
        self.numeric_validator = NumericValidator()
        self.citation_validator = CitationValidator()
        self.report_validator = ReportValidator()

    def verify(
        self,
        answer: str,
        evidence: list[dict],
        report: dict | None = None,
    ) -> dict:

        evidence_ids = [
            item.get("evidence_id")
            for item in evidence
            if isinstance(item, dict)
            and item.get("evidence_id")
        ]

        status = "passed"
        failures = []
        numeric_results = []

        # --------------------------------------------------
        # 1. CITATION VALIDATION
        # --------------------------------------------------

        if not self.citation_validator.validate(
            answer,
            evidence_ids,
        ):
            failures.append(
                "citation_validation_failed"
            )
            status = "failed"

        # --------------------------------------------------
        # 2. NUMERIC VALIDATION
        # --------------------------------------------------

        for item in evidence:

            if not isinstance(item, dict):
                continue

            if item.get("evidence_type") != "data_result":
                continue

            result = self.numeric_validator.validate_data_result(
                answer,
                item,
            )

            numeric_results.append(
                {
                    "evidence_id": item.get("evidence_id"),
                    **result,
                }
            )

            if result.get("checked") and not result.get("valid"):
                failures.append(
                    "numeric_validation_failed"
                )
                status = "failed"

        # --------------------------------------------------
        # 3. REPORT VALIDATION
        # --------------------------------------------------

        if report and not self.report_validator.validate(
            report
        ):
            failures.append(
                "report_structure_invalid"
            )
            status = "failed"

        # --------------------------------------------------
        # FINAL RESULT
        # --------------------------------------------------

        return {
            "verification_status": status,
            "failures": failures,
            "numeric_validation": numeric_results,
        }