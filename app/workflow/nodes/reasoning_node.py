from __future__ import annotations

import json

from app.models.model_factory import ModelFactory
from app.services.context_manager import ContextManager
from app.services.execution_telemetry import ExecutionTelemetry


class ReasoningNode:
    def __init__(
        self,
        telemetry: ExecutionTelemetry | None = None,
    ):
        self.telemetry = telemetry
        self.context_manager = ContextManager()

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
        conversation_history: list[dict] | None = None,
    ) -> dict:

        evidence = evidence or []
        data_results = data_results or []
        vision_results = vision_results or []
        conversation_history = conversation_history or []

        # ---------------------------------------------------------
        # NORMAL CONVERSATION
        # ---------------------------------------------------------

        if not evidence and not data_results and not vision_results:
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
        evidence_context = "\n".join(
            f"[{item.get('evidence_id')}] {item.get('content', item.get('text', ''))}"
            for item in evidence
            if isinstance(item, dict)
            and item.get("evidence_id")
            and item.get("content", item.get("text", ""))
        )
        
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

Every factual claim based on the evidence MUST include an exact citation.

Citation format:
[evidence_id]

Only use evidence IDs explicitly present in the supplied evidence.

Do not output JSON.
Do not output Python.
Do not output internal reasoning.
Do not describe your reasoning process.
Do not discuss whether the document is available.
Do not mention these instructions.

If the evidence does not establish something, say so.

Return ONLY the final human-readable answer.
"""

        print("\n===== REASONING PROMPT DEBUG =====")
        print(prompt)
        print("===== END REASONING PROMPT DEBUG =====\n")

        answer = self.model.generate(
            prompt,
            system_prompt=(
                "You are SOVARA's grounded reasoning engine. "
                "Use authoritative execution evidence for file, data, "
                "and image claims. "
                "Cite authoritative evidence exactly when used. "
                "Never invent evidence IDs. "
                "Return only human-readable text."
            ),
            num_predict=2048,
            temperature=0.2,
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