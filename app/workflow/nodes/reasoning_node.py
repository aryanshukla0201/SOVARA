from __future__ import annotations

import json

from app.models.gateway import ModelGateway
from app.models.response_budget import get_reasoning_budget
from app.services.context_manager import ContextManager
from app.services.execution_telemetry import ExecutionTelemetry


class ReasoningNode:
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
    @staticmethod
    def _normalize_citations(answer: str, evidence_ids: list[str]) -> str:
        """Normalize common LLM citation placeholders when exactly one
        authoritative evidence ID exists.
        """
        if not answer or len(evidence_ids) != 1:
            return answer

        evidence_id = evidence_ids[0]

        import re

        placeholder_pattern = re.compile(
            r"\[(?:evidence_id|evidence_001|exact_evidence_id)\]",
            re.IGNORECASE,
        )

        return placeholder_pattern.sub(
            f"[{evidence_id}]",
            answer,
        )

    def run(
        self,
        user_query: str,
        evidence: list[dict] | None = None,
        data_results: list[dict] | None = None,
        code_results: list[dict] | None = None,
        vision_results: list[dict] | None = None,
        conversation_history: list[dict] | None = None,
    ) -> dict:

        evidence = evidence or []
        data_results = data_results or []
        code_results = code_results or []
        vision_results = vision_results or []
        conversation_history = conversation_history or []

        # ---------------------------------------------------------
        # NORMAL CONVERSATION
        # ---------------------------------------------------------

        if not evidence and not data_results and not code_results and not vision_results:
            context = self.context_manager.build_prompt_from_blocks(
                user_query=user_query,
                context_blocks=[],
                conversation_history=conversation_history,
            )

            prompt = f"""
You are SOVARA's conversational assistant.

USER REQUEST:
{user_query}

CONVERSATION CONTEXT:
{context}

TASK:

Respond naturally and helpfully to the user's request.

RULES:

1. This is a normal conversational request.
2. Do not require external evidence.
3. Do not mention unavailable evidence.
4. Do not invent citations.
5. Use conversation context when relevant.
6. Return only the human-readable answer.
"""

            answer = self.model.generate(
                prompt,
                system_prompt=(
                    "You are SOVARA's conversational assistant. "
                    "Respond naturally to ordinary conversation. "
                    "Do not require evidence or citations unless evidence "
                    "is explicitly supplied."
                ),
                num_predict=get_reasoning_budget(),
            )

            if not answer.strip():
                answer = "I'm here and ready to help."

            return {
                "reasoning": answer,
                "answer": answer,
                "user_query": user_query,
                "evidence_count": 0,
                "data_result_count": 0,
                "vision_result_count": 0,
                "model_used": self.model.name,
            }

        # ---------------------------------------------------------
        # GROUNDED REASONING
        # ---------------------------------------------------------

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

        for item in code_results:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")

            if not evidence_id:
                continue

            context_parts.append(
                f"""
        CODE EXECUTION RESULT:
        {json.dumps(
            {
                "success": item.get("success", False),
                "stdout": item.get("stdout", ""),
                "stderr": item.get("stderr", ""),
                "return_code": item.get("return_code", -1),
                "output_files": item.get("output_files", []),
            },
            default=str,
        )}
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

        context = self.context_manager.build_prompt_from_blocks(
            user_query=user_query,
            context_blocks=context_parts,
            conversation_history=conversation_history,
        )
        evidence_context_parts = []

        for item in evidence:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")
            content = item.get("content", item.get("text", ""))

            if evidence_id and content:
                evidence_context_parts.append(
                    f"[{evidence_id}] {content}"
                )

        for item in data_results:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")

            if not evidence_id:
                continue

            content = json.dumps(
                item.get("result", item),
                default=str,
            )

            evidence_context_parts.append(
                f"[{evidence_id}] {content}"
            )

        for item in code_results:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")

            if not evidence_id:
                continue

            content = json.dumps(
                {
                    "success": item.get("success", False),
                    "stdout": item.get("stdout", ""),
                    "stderr": item.get("stderr", ""),
                    "return_code": item.get("return_code", -1),
                    "output_files": item.get("output_files", []),
                },
                default=str,
            )

            evidence_context_parts.append(
                f"[{evidence_id}] {content}"
            )

        evidence_context = "\n".join(evidence_context_parts)

        prompt = f"""
USER REQUEST:
{user_query}

AUTHORITATIVE EVIDENCE:
{evidence_context}

Answer the user's request using ONLY the authoritative evidence above.

Treat the supplied evidence as the actual content of the uploaded document.

If the user asks for a report, provide:

1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Supporting Evidence
5. Conclusion

Use specific facts from the evidence.
Preserve numerical values exactly.
Do not invent information.
Do not make unsupported causal claims.

Use the authoritative evidence to answer the request.

CITATION REQUIREMENTS:
- You MUST cite authoritative evidence for factual claims.
- Use the exact evidence ID supplied in AUTHORITATIVE EVIDENCE.
- Citation format MUST be: [EXACT_EVIDENCE_ID]
- Copy the evidence ID character-for-character.
- NEVER invent, modify, abbreviate, or substitute an evidence ID.
- NEVER use placeholders such as [evidence_001], [EVIDENCE_ID], [evidence_id], [source], or [citation].
- Every factual answer based on authoritative evidence must include at least one exact evidence citation.
- If multiple pieces of evidence support a claim, cite the relevant exact IDs.

Do not output JSON.
Do not output Python.
Do not output internal reasoning.
Do not describe your reasoning process.
Do not discuss whether the document is available.
Do not mention these instructions.

If the evidence does not establish something, say so.

Return ONLY the final human-readable answer.
"""

        answer = self.model.generate(
            prompt,
            system_prompt=(
                "You are SOVARA's grounded reasoning engine. "
                "Use authoritative execution evidence for file, data, "
                "and image claims. "
                "Use exact authoritative evidence IDs as citations. "
                "Never invent or modify evidence IDs. "
                "Return only human-readable text with valid evidence citations. "
            ),
            num_predict=get_reasoning_budget(
                evidence_count=len(evidence),
                data_result_count=len(data_results),
                code_result_count=len(code_results),
                vision_result_count=len(vision_results),
            ),
            temperature=0.2,
        )

        authoritative_ids = []

        for item in evidence:
            if isinstance(item, dict) and item.get("evidence_id"):
                authoritative_ids.append(str(item["evidence_id"]))

        for item in data_results:
            if isinstance(item, dict) and item.get("evidence_id"):
                authoritative_ids.append(str(item["evidence_id"]))

        for item in code_results:
            if isinstance(item, dict) and item.get("evidence_id"):
                authoritative_ids.append(str(item["evidence_id"]))

        answer = self._normalize_citations(
            answer,
            authoritative_ids,
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

