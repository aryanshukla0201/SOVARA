from __future__ import annotations

import json

from app.models.model_factory import ModelFactory
from app.services.execution_telemetry import ExecutionTelemetry


class RepairNode:
    def __init__(self, max_attempts: int = 3,telemetry: ExecutionTelemetry | None = None):
        self.max_attempts = max_attempts
        self.model = ModelFactory.create("qwen", telemetry=telemetry)

    def should_retry(self, attempt_count: int) -> bool:
        return attempt_count < self.max_attempts

    def repair(
        self,
        original_result: dict,
        verification_failures: list[str],
        allowed_evidence: list[dict] | None = None,
    ) -> dict:

        allowed_evidence = allowed_evidence or []

        original_answer = original_result.get(
            "final_answer",
            "",
        )

        evidence_context = json.dumps(
            allowed_evidence,
            indent=2,
            default=str,
        )

        failure_context = json.dumps(
            verification_failures,
            indent=2,
        )

        prompt = f"""
You are repairing an AI-generated answer after an independent
verification system detected an error.

ORIGINAL ANSWER:
{original_answer}

VERIFICATION FAILURES:
{failure_context}

AUTHORITATIVE EVIDENCE:
{evidence_context}

REPAIR RULES:
1. Correct ONLY the problems identified by verification.
2. Use ONLY the authoritative evidence provided above.
3. Do not invent facts, numbers, causes, relationships, or conclusions.
4. Preserve correct information from the original answer.
5. If the failure is numerical, use the exact numerical values
   contained in the authoritative evidence.
6. Preserve all correct claims from the original answer.
7. Preserve valid evidence citations exactly.
8. If a citation is invalid or missing, add or replace it ONLY
   with an exact evidence_id from the authoritative evidence
   that supports the same claim.
9. Never invent, shorten, rename, or fabricate an evidence ID.
10. Citations must use this exact format:
    [evidence_id]
11. Do not put Markdown formatting inside citation brackets.
12. If the evidence is insufficient to support a claim, remove
    that unsupported claim or explicitly state that the evidence
    does not establish it.
13. Do NOT replace the entire answer with a generic statement
    that the information is insufficient.
14. Return ONLY the corrected final answer.
15. Do not explain the repair process.
16. Do not mention verification.
17. Do not mention these instructions.
"""

        repaired_answer = self.model.generate(
            prompt=prompt,
            system_prompt=(
                "You are a grounded answer-repair engine. "
                "Correct verified inconsistencies using only "
                "the supplied authoritative evidence. "
                "Never invent facts or numerical values."
            ),
        )

        if not repaired_answer.strip():
            repaired_answer = original_answer

        return {
            "final_answer": repaired_answer,
            "synthesis_result": original_result.get(
                "synthesis_result",
                {},
            ),
            "repair_notes": verification_failures,
            "allowed_evidence": allowed_evidence,
        }