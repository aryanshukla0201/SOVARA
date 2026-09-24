from __future__ import annotations

import json

from app.models.gateway import ModelGateway
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

        self.model = model or ModelGateway(
            telemetry=telemetry,
        ).resolve("reasoning")

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

3. Evidence IDs are provenance identifiers supplied in the
AUTHORITATIVE EVIDENCE section and may be used only as citation markers.

4. Every factual paragraph MUST contain at least one citation.

5. The ONLY valid citation format is:
   [EXACT_EVIDENCE_ID]

   Replace EXACT_EVIDENCE_ID with the exact evidence_id supplied
   in the AUTHORITATIVE EVIDENCE section.

6. Copy evidence IDs character-for-character inside square brackets.

7. NEVER invent, modify, abbreviate, or substitute an evidence ID.

8. NEVER use citation formats such as:
   [EVIDENCE_ID: data_test_ev_001]
   [evidence_id]
   [citation: data_test_ev_001]
   [source]

9. Internal IDs such as request IDs and execution IDs must never be
included unless they are being used as an exact supplied evidence_id
citation.

7. NEVER use citation placeholders such as [evidence_id], [citation],
[source], or [code_12345678].

8. Preserve exact numerical values from the authoritative evidence.

9. Do NOT output JSON.

10 . Do NOT output Python dictionaries.

11. Do NOT output internal execution state.

12. Do NOT output evidence lists.

13. Do NOT explain the verification process.

14 . Return ONLY a clean human-readable final answer.

15. If the evidence cannot establish a claim, explicitly state that
the evidence does not establish it.

16. Preserve exact numerical values from evidence.

17. When a highly relevant evidence item directly answers the question,
do not substitute information from a lower-relevance unrelated item.

19. When a highly relevant evidence item directly answers the question,
do not substitute information from a lower-relevance unrelated item.

20. If the top-ranked evidence clearly answers the question, prioritize it
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
                "Use citations exactly as [EXACT_EVIDENCE_ID]. "
                "Copy supplied evidence IDs character-for-character. "
                "Never add labels such as EVIDENCE_ID: inside citations. "
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

