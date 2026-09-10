from __future__ import annotations

import re
from typing import Any

from app.models.qwen_adapter import QwenAdapter


class CitationValidator:
    def validate(
        self,
        answer: str,
        evidence_ids: list[str],
    ) -> bool:
        if not evidence_ids:
            return True

        cited_ids = re.findall(
            r"\[([^\]]+)\]",
            answer,
        )

        if not cited_ids:
            return False

        valid_ids = set(evidence_ids)

        return all(
            citation in valid_ids
            for citation in cited_ids
        )


class RepairNode:
    def __init__(
        self,
        max_attempts: int = 3,
        telemetry=None,
    ):
        self.max_attempts = max_attempts
        self.telemetry = telemetry

    def repair(
        self,
        state: dict[str, Any],
        failures: list[str],
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:

        answer = state.get("final_answer", "")
        synthesis_result = state.get(
            "synthesis_result",
            {},
        ) or {}

        evidence_ids = []

        for item in evidence:
            evidence_id = item.get("evidence_id")

            if evidence_id:
                evidence_ids.append(
                    str(evidence_id)
                )

        validator = CitationValidator()

        if validator.validate(
            answer,
            evidence_ids,
        ):
            return {
                "final_answer": answer,
                "synthesis_result": synthesis_result,
            }

        grounded_evidence = []

        sorted_evidence = sorted(
            evidence,
            key=lambda item: item.get("relevance_score", 0),
            reverse=True,
        )

        if sorted_evidence:
            top_score = sorted_evidence[0].get("relevance_score", 0)
            sorted_evidence = [
                item
                for item in sorted_evidence
                if item.get("relevance_score", 0) >= top_score - 0.10
            ]


        for item in sorted_evidence:
            evidence_id = item.get("evidence_id")

            content = (
                item.get("content")
                or item.get("text")
                or item.get("description")
                or ""
            )

            if not evidence_id or not content:
                continue

            grounded_evidence.append(
                f"[{evidence_id}] {content}"
            )

        prompt = f"""
Repair the following answer using ONLY the supplied evidence.

Original answer:
{answer}

Verification failures:
{failures}

Evidence:
{chr(10).join(grounded_evidence)}

Requirements:
- Preserve correct information.
- Remove unsupported claims.
- Every factual claim must cite an exact evidence ID.
- Use citations in the format [evidence_id].
- Do not invent evidence IDs.
- Return only the repaired answer.
"""

        adapter = QwenAdapter(
            telemetry=self.telemetry
        )

        repaired_answer = adapter.generate(
            prompt,
            system_prompt=(
                "You are SOVARA's citation repair engine. "
                "Return ONLY the repaired human-readable answer. "
                "Do not explain your reasoning. "
                "Do not describe the task. "
                "Do not output analysis or meta-commentary. "
                "Do not output <think> tags. "
                "Every factual claim must use an exact supplied evidence ID."
            ),
            num_predict=2048,
            temperature=0.1,
        )

        repaired_answer = re.sub(
            r"<think>.*?</think>",
            "",
            repaired_answer,
            flags=re.DOTALL,
        ).strip()

        repaired_answer = re.sub(
            r"^.*?</think>\s*",
            "",
            repaired_answer,
            flags=re.DOTALL,
        ).strip()
        
        return {
            "final_answer": repaired_answer,
            "synthesis_result": {
                **synthesis_result,
                "answer": repaired_answer,
            },
        }