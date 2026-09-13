from __future__ import annotations

import json

from app.models.model_factory import ModelFactory
from app.services.execution_telemetry import ExecutionTelemetry
from app.services.context_manager import ContextManager


class SynthesisNode:
    def __init__(
        self,
        model=None,
        telemetry: ExecutionTelemetry | None = None,
    ):
        self.telemetry = telemetry
        self.context_manager = ContextManager()

        self.model = model or ModelFactory.create(
            "qwen",
            telemetry=telemetry,
        )

    def run(
        self,
        user_query: str,
        evidence: list[dict],
        data_results: list[dict],
        code_results: list[dict],
        vision_results: list[dict],
        conversation_history: list[dict] | None = None,
    ) -> dict:

        grounded_evidence = []

        for item in code_results:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")

            if evidence_id:
                grounded_evidence.append({
                    "evidence_id": evidence_id,
                    "evidence_type": "code_execution_result",
                    "relevance_score": 1.0,
                    "content": json.dumps(
                        {
                            "success": item.get("success", False),
                            "stdout": item.get("stdout", ""),
                            "stderr": item.get("stderr", ""),
                            "return_code": item.get("return_code", -1),
                            "output_files": item.get("output_files", []),
                        },
                        default=str,
                    ),
                })

        for item in data_results:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")

            if evidence_id:
                grounded_evidence.append({
                    "evidence_id": evidence_id,
                    "evidence_type": "data_result",
                    "relevance_score": 1.0,
                    "content": json.dumps(
                        item.get("result", item),
                        default=str,
                    ),
                })

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

                grounded_evidence.append({
                    "evidence_id": evidence_id,
                    "evidence_type": "vision",
                    "source_filename": item.get(
                        "source_file",
                        "",
                    ),
                    "content": observation.get(
                        "description",
                        "",
                    ),
                    "confidence": observation.get(
                        "confidence",
                    ),
                    "relevance_score": observation.get(
                        "confidence",
                        0.0,
                    ),
                })

        grounded_evidence.sort(
            key=lambda item: float(
                item.get("relevance_score", 0.0) or 0.0
            ),
            reverse=True,
        )

        evidence_context = "\n".join(
            f"[{item['evidence_id']}] {item['content']}"
            for item in grounded_evidence
            if item.get("content")
        )

        conversation_context = self.context_manager.build_prompt_from_blocks(
            user_query=user_query,
            context_blocks=[
                f"AUTHORITATIVE EVIDENCE:\n{evidence_context}"
            ],
            conversation_history=conversation_history,
        )

        prompt = f"""
You are the final answer generation stage of SOVARA.

CONVERSATION CONTEXT:
{conversation_context}

RETRIEVAL PRIORITY:

- Evidence is ordered from highest relevance to lowest relevance.
- Prefer the highest-relevance evidence when answering.
- Use lower-ranked evidence only when it directly contributes to the answer.
- Do NOT let unrelated lower-ranked evidence override highly relevant evidence.
- If one evidence item directly answers the user's question, answer from that
  evidence rather than combining it with unrelated documents.
- Evidence from different documents must not be combined unless the documents
  are actually relevant to the same question.

RULES:

1. Answer ONLY using the authoritative evidence above.

2. Use the authoritative evidence to support factual claims.

3. Evidence IDs are internal traceability metadata.

4. NEVER expose evidence IDs, internal IDs, request IDs,
execution IDs, or other internal metadata in the final answer.

5. Do NOT write citations such as [evidence_id] or [code_12345678].

6. Return a clean human-readable answer without citation markers.

7. Preserve exact numerical values from the authoritative evidence.

8. Do NOT output JSON.

9. Do NOT output Python dictionaries.

10. Do NOT output internal execution state.

11. Do NOT output evidence lists.

12. Do NOT explain the verification process.

13. Return ONLY a clean human-readable final answer.

14. If the evidence cannot establish a claim, explicitly state that
the evidence does not establish it.

15. Do not make unsupported causal claims.

16. Preserve exact numerical values from evidence.

17. Every paragraph containing factual information must contain
at least one valid citation.

18. When a highly relevant evidence item directly answers the question,
do not substitute information from a lower-relevance unrelated item.

19. If the top-ranked evidence clearly answers the question, prioritize it
over all unrelated lower-ranked evidence.

Before returning the answer, internally verify that every citation
exactly matches one of the supplied evidence_id values.

Return ONLY the final answer.
"""

        result = self.model.generate(
            prompt,
            system_prompt=(
                "You are SOVARA's final grounded answer generator. "
                "Use the highest-relevance relevant evidence first. "
                "Do not allow unrelated evidence to override relevant evidence. "
                "Return only a clean human-readable answer. "
                "Use authoritative evidence to support the answer. "
                "Never expose evidence IDs or internal metadata. "
                "Return only clean human-readable text."
            ),
        )

        return {
            "answer": result,
            "evidence_references": [
                item["evidence_id"]
                for item in grounded_evidence
            ],
            "confidence": 0.85,
        }