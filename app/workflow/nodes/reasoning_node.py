from __future__ import annotations

import json

from app.models.model_factory import ModelFactory
from app.services.execution_telemetry import ExecutionTelemetry


class ReasoningNode:
    def __init__(self,telemetry: ExecutionTelemetry | None = None):
        self.model = ModelFactory.create("qwen", telemetry=telemetry)

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

        # -------------------------------------------------
        # DOCUMENT EVIDENCE
        # -------------------------------------------------
        if evidence:

            document_context = []

            for item in evidence[:3]:

                text = item.get("text", "").strip()
                evidence_id = item.get("evidence_id", "")
                source_filename = item.get("source_filename", "")
                page_number = item.get("page_number", "")

                if not text:
                    continue

                text = text[:1500]

                document_context.append(
                    f"""
SOURCE: {source_filename}
PAGE: {page_number}
EVIDENCE ID: {evidence_id}

CONTENT:
{text}
"""
                )

            if document_context:

                context_parts.append(
                    "DOCUMENT EVIDENCE:\n"
                    + "\n\n".join(document_context)
                )

        # -------------------------------------------------
        # DATA EVIDENCE
        # -------------------------------------------------
        if data_results:

            data_context = []

            for item in data_results:

                if not isinstance(item, dict):
                    continue

                evidence_id = item.get("evidence_id", "")
                tool_used = item.get("tool_used", "")
                file_type = item.get("file_type", "")
                result = item.get("result", {})

                data_context.append(
                    f"""
DATA EVIDENCE ID: {evidence_id}
TOOL: {tool_used}
FILE TYPE: {file_type}

RESULT:
{json.dumps(result, indent=2, default=str)}
"""
                )

            if data_context:

                context_parts.append(
                    "DATA ANALYSIS RESULTS:\n"
                    + "\n\n".join(data_context)
                )

        # -------------------------------------------------
        # VISION RESULTS
        # -------------------------------------------------
        if vision_results:

            vision_context = []

            for item in vision_results:

                if not isinstance(item, dict):
                    continue

                evidence_id = item.get("evidence_id", "")
                result = item.get("result", item)

                vision_context.append(
                    f"""
VISION EVIDENCE ID: {evidence_id}

RESULT:
{json.dumps(result, indent=2, default=str)}
"""
                )

            if vision_context:

                context_parts.append(
                    "VISION ANALYSIS RESULTS:\n"
                    + "\n\n".join(vision_context)
                )

        # -------------------------------------------------
        # NO CONTEXT AVAILABLE
        # -------------------------------------------------
        if not context_parts:

            answer = (
                "The available execution results did not contain "
                "enough information to produce a detailed analysis."
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

        # -------------------------------------------------
        # BUILD CONTEXT
        # -------------------------------------------------
        context = "\n\n".join(context_parts)

        # -------------------------------------------------
        # LLM PROMPT
        # -------------------------------------------------
        prompt = f"""
USER REQUEST:
{user_query}

AVAILABLE EXECUTION RESULTS:

{context}

TASK:

Answer the user's request using ONLY the information provided in
the execution results above.

GROUNDING AND CITATION RULES:

1. Do not invent facts, numbers, explanations, causes, trends,
   relationships, or conclusions.

2. Every claim based on DOCUMENT EVIDENCE must include the exact
   document evidence ID that supports the claim.

3. Every claim based on DATA ANALYSIS RESULTS must include the exact
   DATA EVIDENCE ID that supports the claim.

4. Every claim based on VISION ANALYSIS RESULTS must include the exact
   VISION EVIDENCE ID that supports the claim.

5. Citations MUST use this exact format:

   [evidence_id]

6. Valid examples:

   The document describes an automated subsidy recommendation system
   [file_12345678_ev_001].

   Revenue increased from 100 to 180, representing an 80% increase
   [data_12345678].

7. Invalid citation formats:

   [**file_12345678_ev_001**]
   (file_12345678_ev_001)
   file_12345678_ev_001
   [file_12345678_ev_001, file_12345678_ev_002]

8. Never put Markdown formatting inside citation brackets.

9. Never modify, shorten, rename, or invent an evidence ID.

10. Only cite evidence IDs that actually appear in the execution
    results above.

11. If multiple evidence items support the same claim, cite them
    separately:

    [evidence_id_1] [evidence_id_2]

12. Do NOT use a DOCUMENT evidence ID to support a DATA claim.

13. Do NOT use a DATA evidence ID to support a DOCUMENT claim.

14. Do NOT infer causation between different sources unless the
    provided evidence explicitly establishes that relationship.

15. Preserve deterministic numerical results exactly.

16. If the data result says:
    start = 100
    end = 180
    percentage_change = 80

    you may state:

    Revenue increased from 100 to 180, representing an 80% increase
    [data_12345678].

17. Do NOT introduce additional numerical claims that are not present
    in the data analysis results.

18. If the available evidence is insufficient to answer part of the
    request, explicitly state that it is insufficient.

19. Clearly distinguish observations from conclusions.

20. Organize the answer with headings or bullet points when useful.

IMPORTANT:

The answer will be automatically checked by a strict verification
system. Citation syntax must be exact.

Return ONLY the final answer for the user.
"""

        # -------------------------------------------------
        # MODEL REASONING
        # -------------------------------------------------
        answer = self.model.generate(
            prompt=prompt,
            system_prompt=(
                "You are a careful AI reasoning engine. "
                "Use only grounded execution results. "
                "Preserve exact evidence citations. "
                "Never invent facts or relationships. "
                "Preserve deterministic numerical results. "
                "Clearly distinguish observations, conclusions, and limitations."
            ),
        )

        # -------------------------------------------------
        # FALLBACK
        # -------------------------------------------------
        if not answer.strip():

            answer = (
                "The reasoning model did not return a response. "
                "Please review the available execution results."
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