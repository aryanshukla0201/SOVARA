from __future__ import annotations


class RepairNode:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def should_retry(self, attempt_count: int) -> bool:
        return attempt_count < self.max_attempts

    def repair(self, original_result: dict, verification_failures: list[str], allowed_evidence: list[dict] | None = None) -> dict:
        repaired = dict(original_result)
        if verification_failures:
            repaired["repair_notes"] = verification_failures
            repaired["allowed_evidence"] = allowed_evidence or []
        return repaired
