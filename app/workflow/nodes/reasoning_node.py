from __future__ import annotations

import json

from app.models.model_factory import ModelFactory


class ReasoningNode:
    def __init__(self):
        self.model = ModelFactory.create("qwen")

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

                # Prevent excessively large prompts
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
        # DATA RESULTS
        # -------------------------------------------------
        if data_results:

            context_parts.append(
                "DATA ANALYSIS RESULTS:\n"
                + json.dumps(
                    data_results,
                    indent=2,
                    default=str,
                )
            )

        # -------------------------------------------------
        # VISION RESULTS
        # -------------------------------------------------
        if vision_results:

            context_parts.append(
                "VISION ANALYSIS RESULTS:\n"
                + json.dumps(
                    vision_results,
                    indent=2,
                    default=str,
                )
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

Answer the user's request using only the information provided in
the execution results above.

Requirements:

1. Produce a clear and useful answer rather than copying the source
   text verbatim.

2. Summarize and interpret the information relevant to the user's
   request.

3. Do not invent information that is not present in the provided
   execution results.

4. When making statements based on document evidence, include the
   corresponding evidence ID in square brackets.

5. For example:
   "The candidate has experience with diffusion-model research
   [test_pdf_001_ev_001]."

6. If data analysis results are provided, explain what the results
   mean rather than simply repeating JSON values.

7. Organize the answer with headings or bullet points when useful.

Return only the final answer for the user.
"""

        # -------------------------------------------------
        # MODEL REASONING
        # -------------------------------------------------
        answer = self.model.generate(
            prompt=prompt,
            system_prompt=(
                "You are a careful AI reasoning engine. "
                "Your job is to analyze grounded evidence and execution "
                "results and produce accurate answers. "
                "Never invent facts. "
                "Prefer concise, structured, evidence-grounded responses."
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