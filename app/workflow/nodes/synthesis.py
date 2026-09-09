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
        vision_results: list[dict],
        conversation_history: list[dict] | None = None,
    ) -> dict:

        grounded_evidence = []

        for item in evidence:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")

            if not evidence_id:
                continue

            grounded_evidence.append({
                "evidence_id": evidence_id,
                "source_filename": item.get("source_filename", ""),
                "page_number": item.get("page_number"),
                "evidence_type": item.get("evidence_type", "document"),
                "relevance_score": item.get("relevance_score", 0.0),
                "content": item.get(
                    "content",
                    item.get("text", ""),
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

2. Every factual claim MUST have at least one citation.

3. Citations MUST use an exact evidence_id from the evidence.

4. Citation format MUST be exactly:
[evidence_id]

5. Example:
The document describes market linkage between farmers and buyers [file_123_ev_001].

6. NEVER write a citation without square brackets.

7. NEVER modify an evidence_id.

8. NEVER invent an evidence_id.

9. NEVER use Markdown inside citation brackets.

10. Multiple citations must be separate:
[file_123_ev_001] [file_123_ev_002]

11. Do NOT output JSON.

12. Do NOT output Python dictionaries.

13. Do NOT output internal execution state.

14. Do NOT output evidence lists.

15. Do NOT explain the verification process.

16. Return ONLY a clean human-readable final answer.

17. If the evidence cannot establish a claim, explicitly state that
the evidence does not establish it.

18. Do not make unsupported causal claims.

19. Preserve exact numerical values from evidence.

20. Every paragraph containing factual information must contain
at least one valid citation.

21. When a highly relevant evidence item directly answers the question,
do not substitute information from a lower-relevance unrelated item.

22. If the top-ranked evidence clearly answers the question, prioritize it
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
                "Every factual claim requires an exact evidence citation. "
                "Never output JSON or internal state. "
                "Never invent evidence IDs."
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