from __future__ import annotations


class ReportValidator:
    def validate(self, report: dict) -> bool:
        if not isinstance(report, dict):
            return False

        if not report.get("title"):
            return False

        sections = report.get("sections")

        if not isinstance(sections, dict):
            return False

        required_sections = [
            "answer",
            "evidence_count",
            "document_results",
            "data_results",
            "vision_results",
        ]

        return all(section in sections for section in required_sections)