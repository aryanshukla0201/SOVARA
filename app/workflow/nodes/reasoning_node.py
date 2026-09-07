from __future__ import annotations

import json

from app.models.model_factory import ModelFactory
from app.services.execution_telemetry import ExecutionTelemetry


class ReasoningNode:
    def __init__(
        self,
        telemetry: ExecutionTelemetry | None = None,
    ):
        self.model = ModelFactory.create(
            "qwen",
            telemetry=telemetry,
        )

    def run(
        self,
        user_query: str,
        evidence: list[dict] | None = None,
        data_results: list[dict] | None = None,
        vision_results: list[dict] | None = None,
    ) -> dict:

        evidence = evidence or []
        data_results = data_results or []
        vision_results = vision_results or []

        context_parts = []

        for item in evidence:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")
            if not evidence_id:
                continue

            content = item.get(
                "content",
                item.get("text", ""),
            )

            if not content:
                continue

            context_parts.append(
                f"""
EVIDENCE ID: {evidence_id}
TYPE: {item.get("evidence_type", "document")}
SOURCE: {item.get("source_filename", "")}
PAGE: {item.get("page_number", "")}

CONTENT:
{content}
"""
            )

        for item in data_results:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")

            if not evidence_id:
                continue

            context_parts.append(
                f"""
EVIDENCE ID: {evidence_id}
TYPE: data_result

RESULT:
{json.dumps(item.get("result", item), indent=2, default=str)}
"""
            )

        for item in vision_results:
            if not isinstance(item, dict):
                continue

            file_id = item.get("file_id", "")
            result = item.get("result", {})

            observations = (
                result.get("observations", [])
                if isinstance(result, dict)
                else []
            )

            for index, observation in enumerate(
                observations,
                start=1,
            ):
                evidence_id = f"{file_id}_ev_{index:03d}"

                context_parts.append(
                    f"""
EVIDENCE ID: {evidence_id}
TYPE: vision
SOURCE: {item.get("source_file", "")}

CONTENT:
{observation.get("description", "")}
"""
                )

        if not context_parts:
            answer = (
                "The available evidence does not contain enough "
                "information to answer the request."
            )

            return {
                "reasoning": answer,
                "answer": answer,
                "user_query": user_query,
                "evidence_count": 0,
                "data_result_count": 0,
                "vision_result_count": 0,
                "model_used": None,
            }

        context = "\n\n".join(context_parts)

        prompt = f"""
USER REQUEST:
{user_query}

AUTHORITATIVE EXECUTION EVIDENCE:

{context}

TASK:

Produce a concise answer to the user's request.

STRICT RULES:

1. Use ONLY the supplied evidence.

2. Every factual claim MUST contain an exact evidence citation.

3. Citation format:
[evidence_id]

4. Only use evidence IDs explicitly supplied above.

5. Never invent or modify evidence IDs.

6. Never output JSON.

7. Never output dictionaries.

8. Never output internal execution state.

9. Do not claim causation unless explicitly supported.

10. Preserve numerical values exactly.

11. Clearly distinguish observations from interpretations.

12. If evidence is insufficient, state that clearly.

13. Return ONLY the human-readable answer.

Before returning, verify every citation against the supplied evidence IDs.
"""

        answer = self.model.generate(
            prompt,
            system_prompt=(
                "You are SOVARA's grounded reasoning engine. "
                "Every factual claim must have an exact evidence citation. "
                "Return only human-readable text. "
                "Never output JSON or internal state."
            ),
        )

        if not answer.strip():
            answer = (
                "The reasoning model did not return a response. "
                "Please review the available evidence."
            )

        return {
            "reasoning": answer,
            "answer": answer,
            "user_query": user_query,
            "evidence_count": len(evidence),
            "data_result_count": len(data_results),
            "vision_result_count": len(vision_results),
            "model_used": self.model.name,
        }