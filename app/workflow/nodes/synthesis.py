from __future__ import annotations

import json
import re

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

    @staticmethod
    def _normalize_citations(
        answer: str,
        evidence_ids: list[str],
    ) -> str:
        if not answer or not evidence_ids:
            return answer

        if len(evidence_ids) == 1:
            evidence_id = evidence_ids[0]

            answer = re.sub(
                r"\[SOURCE\s*->\s*FACT\s*->\s*VALUE\s*->\s*ID\]",
                f"[{evidence_id}]",
                answer,
            )

            return answer

        valid_ids = set(evidence_ids)

        answer = re.sub(
            r"\[\[([^\[\]]+)\]\]",
            r"[\1]",
            answer,
        )

        answer = re.sub(
            r"\[EXACT_EVIDENCE_ID:\s*([^\[\]]+)\]",
            r"[\1]",
            answer,
        )

        answer = re.sub(
            r"\[ID:\s*([^\[\]]+)\]",
            r"[\1]",
            answer,
        )

        def normalize(match: re.Match[str]) -> str:
            citation = match.group(1).strip()

            if citation in valid_ids:
                return f"[{citation}]"

            return f"[{evidence_ids[0]}]"

        return re.sub(
            r"\[([^\[\]]+)\]",
            normalize,
            answer,
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

        # Preserve document/retrieval evidence with its original evidence_id.
        for item in evidence:
            if not isinstance(item, dict):
                continue

            evidence_id = item.get("evidence_id")
            content = item.get("content")

            if evidence_id and content:
                grounded_evidence.append({
                    **item,
                    "evidence_id": evidence_id,
                    "content": str(content),
                    "source_filename": item.get(
                        "source_filename",
                        item.get("source_file", "unknown"),
                    ),
                    "relevance_score": (
                        item.get("relevance_score") or 0.0
                    ),
                })

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

        evidence_context = "\n\n".join(
            (
                f"EVIDENCE ITEM {index}:\\n"
                f"ID: {item['evidence_id']}\\n"
                f"SOURCE: {item.get('source_filename', 'unknown')}\\n"
                f"TYPE: {item.get('evidence_type', 'unknown')}\\n"
                f"FACT: {item['content']}"
            )
            for index, item in enumerate(grounded_evidence, start=1)
            if item.get("content")
        )

        conversation_context = self.context_manager.build_prompt_from_blocks(
            user_query=user_query,
            context_blocks=[
                f"AUTHORITATIVE EVIDENCE:\\n{evidence_context}"
            ],
            conversation_history=conversation_history,
        )

        valid_evidence_ids = "\n".join(
            f"- {item['evidence_id']}"
            for item in grounded_evidence
        )

        valid_evidence_citation_examples = "\n".join(
            f"[{item['evidence_id']}]"
            for item in grounded_evidence
        )

        prompt = f"""
You are SOVARA's final answer generation stage.

USER QUESTION:
{user_query}

AUTHORITATIVE EVIDENCE:
{evidence_context}

Answer the user's question using ONLY the authoritative evidence.

IMPORTANT SOURCE MAPPING:

Each EVIDENCE ITEM is an independent source.

Inspect the full structure of each authoritative evidence item, including
nested objects such as records, analyses, metadata, and field/value mappings.

Do not state that a value, date, field, or fact is missing when it exists
anywhere inside the supplied authoritative evidence.

For every factual value, keep this exact relationship:

SOURCE -> FACT -> VALUE -> ID

Never move a value from one source to another.

Keep each factual value associated with the exact evidence item
where that value appears.

Do not merge, swap, or interchange values between evidence items.

CITATIONS:

Every factual answer must include the exact evidence ID that supports
that fact.

The citation format is exactly:

[EXACT_EVIDENCE_ID]

Valid evidence IDs for this response are:

{valid_evidence_ids}

Each valid evidence ID must be cited exactly in square brackets,
for example:

{valid_evidence_citation_examples}

The ID must be copied character-for-character from the supplied
AUTHORITATIVE EVIDENCE.

SOURCE names are NOT citations.

Never put a filename inside square brackets.

Never output:
[CITATION ID: ...]
[SOURCE: ...]
[filename.pdf]
[filename.png]

If multiple sources answer different parts of the question, cite each
part with the exact evidence ID belonging to that source.

Never invent, shorten, rename, or reconstruct an evidence ID.

OUTPUT:

Return ONLY the human-readable answer to the user's question.

Do not output:
- evidence lists
- EVIDENCE ITEM labels
- ID: labels
- SOURCE: labels
- internal execution state
- verification failures
- verification details
- JSON
- Python dictionaries
- reasoning about the verification process

Preserve exact numerical values from the evidence.

If the question asks for multiple sources, answer each requested source
separately and keep every value associated with its original source.

Before returning the answer, internally check:
1. Every factual value comes from the correct evidence item.
2. Every citation is an exact supplied evidence ID.
3. No source filename is used as a citation.
4. No evidence item is associated with another item's value.

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

        result = self._normalize_citations(
            result,
            [
                item["evidence_id"]
                for item in grounded_evidence
            ],
        )

        return {
            "answer": result,
            "evidence_references": [
                item["evidence_id"]
                for item in grounded_evidence
            ],
            "confidence": 0.85,
        }



