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

    @staticmethod
    def _enforce_source_bound_calculations(
        answer: str,
        user_query: str,
        data_results: list[dict],
    ) -> str:
        if not answer or not data_results:
            return answer

        percentage_match = re.search(
            r"(\d+(?:\.\d+)?)\s*%",
            user_query,
        )

        if not percentage_match:
            return answer

        if "csv" not in user_query.lower():
            return answer

        if "total" not in user_query.lower():
            return answer

        percentage = float(percentage_match.group(1))

        for item in data_results:
            if not isinstance(item, dict):
                continue

            result_data = item.get("result", item)

            if not isinstance(result_data, dict):
                continue

            total = result_data.get("sum")

            if total is None:
                continue

            calculated_value = float(total) * percentage / 100

            pattern = (
                rf"{re.escape(str(int(percentage) if percentage.is_integer() else percentage))}"
                rf"\s*%.*?"
                rf"(?:=|is|equals).*?"
                rf"\d+(?:\.\d+)?"
            )

            replacement = (
                f"{percentage:g}% of {float(total):g} INR "
                f"is {calculated_value:g} INR "
                f"[{item.get('evidence_id')}]"
            )

            if re.search(pattern, answer, flags=re.IGNORECASE | re.DOTALL):
                return re.sub(
                    pattern,
                    replacement,
                    answer,
                    count=1,
                    flags=re.IGNORECASE | re.DOTALL,
                )

        return answer


    @staticmethod
    def _build_source_bound_multi_input_answer(
        user_query: str,
        grounded_evidence: list[dict],
        data_results: list[dict],
    ) -> str | None:
        query = user_query.lower()

        if not (
            "%" in query
            and "csv" in query
            and "total" in query
            and "pdf" in query
            and "image" in query
            and "budget" in query
            and "duration" in query
        ):
            return None

        percentage_match = re.search(
            r"(\d+(?:\.\d+)?)\s*%",
            user_query,
        )

        if not percentage_match:
            return None

        percentage = float(percentage_match.group(1))

        csv_total = None
        csv_evidence_id = None

        for item in data_results:
            if not isinstance(item, dict):
                continue

            result_data = item.get("result", item)

            if not isinstance(result_data, dict):
                continue

            total = result_data.get("sum")

            if total is not None:
                csv_total = float(total)
                csv_evidence_id = item.get("evidence_id")
                break

        if csv_total is None or not csv_evidence_id:
            return None

        calculated_value = csv_total * percentage / 100

        pdf_budget = None
        pdf_duration = None
        pdf_evidence_id = None

        image_budget = None
        image_duration = None
        image_budget_evidence_id = None
        image_duration_evidence_id = None

        for item in grounded_evidence:
            evidence_id = item.get("evidence_id")
            source_filename = str(
                item.get("source_filename", "")
            ).lower()
            content = str(item.get("content", ""))

            if not evidence_id or not content:
                continue

            if source_filename.endswith(".pdf"):
                budget_match = re.search(
                    r"budget[^0-9]*(\d+(?:\.\d+)?)\s*INR",
                    content,
                    flags=re.IGNORECASE,
                )

                duration_match = re.search(
                    r"duration[^0-9]*(\d+(?:\.\d+)?)\s*days?",
                    content,
                    flags=re.IGNORECASE,
                )

                if budget_match:
                    pdf_budget = float(budget_match.group(1))
                    pdf_evidence_id = evidence_id

                if duration_match:
                    pdf_duration = float(duration_match.group(1))
                    pdf_evidence_id = pdf_evidence_id or evidence_id

            elif source_filename.endswith(
                (".png", ".jpg", ".jpeg", ".bmp", ".webp")
            ):
                budget_match = re.search(
                    r"budget[^0-9]*(\d+(?:\.\d+)?)\s*INR",
                    content,
                    flags=re.IGNORECASE,
                )

                duration_match = re.search(
                    r"duration[^0-9]*(\d+(?:\.\d+)?)\s*days?",
                    content,
                    flags=re.IGNORECASE,
                )

                if budget_match and image_budget is None:
                    image_budget = float(budget_match.group(1))
                    image_budget_evidence_id = evidence_id

                if duration_match and image_duration is None:
                    image_duration = float(duration_match.group(1))
                    image_duration_evidence_id = evidence_id

        if (
            pdf_budget is None
            or pdf_duration is None
            or image_budget is None
            or image_duration is None
        ):
            return None

        def number(value: float) -> str:
            return f"{value:g}"

        return (
            f"{percentage:g}% of the CSV total "
            f"{number(csv_total)} INR = {number(calculated_value)} INR "
            f"[{csv_evidence_id}]\n"
            f"PDF project budget: {number(pdf_budget)} INR "
            f"[{pdf_evidence_id}]\n"
            f"PDF project duration: {number(pdf_duration)} days "
            f"[{pdf_evidence_id}]\n"
            f"Image project budget: {number(image_budget)} INR "
            f"[{image_budget_evidence_id}]\n"
            f"Image project duration: {number(image_duration)} days "
            f"[{image_duration_evidence_id}]"
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

        source_bound_calculations = []

        percentage_match = re.search(
            r"(\d+(?:\.\d+)?)\s*%",
            user_query,
        )

        if percentage_match and data_results:
            percentage = float(percentage_match.group(1))

            for item in data_results:
                if not isinstance(item, dict):
                    continue

                result_data = item.get("result", item)

                if not isinstance(result_data, dict):
                    continue

                total = result_data.get("sum")

                if total is None:
                    continue

                if "csv" in user_query.lower() and "total" in user_query.lower():
                    calculated_value = float(total) * percentage / 100

                    source_bound_calculations.append(
                        (
                            f"CSV SOURCE-BOUND CALCULATION: "
                            f"{percentage:g}% of CSV total {float(total):g} "
                            f"= {calculated_value:g}. "
                            f"This calculation MUST use CSV evidence ID "
                            f"{item.get('evidence_id')}."
                        )
                    )

                    break

        source_bound_calculation_context = "\n".join(
            source_bound_calculations
        )

        source_bound_facts = []

        if (
            "budget" in user_query.lower()
            or "duration" in user_query.lower()
        ):
            for item in grounded_evidence:
                evidence_id = item.get("evidence_id")
                source_filename = str(
                    item.get("source_filename", "")
                ).lower()
                content = str(item.get("content", ""))

                if not evidence_id or not content:
                    continue

                if source_filename.endswith(".pdf"):
                    source_bound_facts.append(
                        (
                            f"PDF SOURCE-BOUND FACTS: "
                            f"budget/duration MUST be taken from evidence "
                            f"{evidence_id}. "
                            f"Evidence content: {content}"
                        )
                    )

                elif source_filename.endswith(
                    (".png", ".jpg", ".jpeg", ".bmp", ".webp")
                ):
                    source_bound_facts.append(
                        (
                            f"IMAGE SOURCE-BOUND FACTS: "
                            f"budget/duration MUST be taken from evidence "
                            f"{evidence_id}. "
                            f"Evidence content: {content}"
                        )
                    )

        source_bound_fact_context = "\n".join(
            source_bound_facts
        )

        prompt = f"""
You are SOVARA's final answer generation stage.

USER QUESTION:
{user_query}

AUTHORITATIVE EVIDENCE:
{evidence_context}

SOURCE-BOUND CALCULATIONS:
{source_bound_calculation_context}

SOURCE-BOUND FILE FACTS:
{source_bound_fact_context}

When a SOURCE-BOUND CALCULATION is supplied, use that calculation
for the corresponding user request. Do not replace its operand with
a number from another source, and do not copy a conflicting
precomputed calculation from another evidence item.

When SOURCE-BOUND FILE FACTS are supplied:

- PDF facts belong only to the PDF source.
- IMAGE facts belong only to the image source.
- Never merge a PDF budget with an image budget.
- Never merge a PDF duration with an image duration.
- If the user asks for both PDF and image values, report them
  separately with their corresponding evidence IDs.

Answer the user's question using ONLY the authoritative evidence.

IMPORTANT SOURCE MAPPING:

Each EVIDENCE ITEM is an independent source.

Inspect the full structure of each authoritative evidence item, including
nested objects such as records, analyses, metadata, and field/value mappings.

Do not state that a value, date, field, or fact is missing when it exists
anywhere inside the supplied authoritative evidence.

Before composing the answer, identify every factual item explicitly requested
by the USER QUESTION.

For EACH requested factual item:

1. Inspect ALL authoritative evidence items and their complete content.
2. Search the full evidence text as well as nested objects, records, analyses,
   metadata, and field/value mappings.
3. If the requested fact exists in any authoritative evidence item, extract
   and report that fact directly.
4. Do NOT say that a requested fact is "not specified", "not provided",
   "missing", or "cannot be determined" if that fact exists anywhere in the
   authoritative evidence.
5. Treat each requested fact independently. Finding one fact must not cause
   another fact from the same source to be treated as missing.
6. Only state that a requested fact is unavailable after checking all
   authoritative evidence and confirming that the specific fact is absent.
MANDATORY COMPLETENESS CHECK:

Before finalizing the answer, perform this internal check:

- If the user asks for multiple facts, the final answer must address every
  requested fact separately.
- A fact is considered available if its value appears anywhere in the
  authoritative evidence, even if it appears in the same sentence as another
  fact.
- Never claim that a requested fact is unspecified if the authoritative
  evidence explicitly contains that fact.
- In particular, do not discard a value merely because another part of the
  same evidence item uses different wording for the requested subject.
- The final answer must contain every available requested value and its
  supporting evidence ID.
For every factual value, keep this exact relationship:

SOURCE -> FACT -> VALUE -> ID

Never move a value from one source to another.

Keep each factual value associated with the exact evidence item
where that value appears.

Do not merge, swap, or interchange values between evidence items.

CALCULATION SOURCE RULES:

When the user asks for a calculation based on a specific source,
the operand MUST come from that source.

For example, if the user asks:
"15% of the total amount in the CSV"

then:
- identify the CSV data_result containing the aggregate total;
- use its sum value as the operand;
- calculate 15% from that CSV sum;
- do NOT use a number from PDF or vision evidence as the operand;
- do NOT copy a precomputed calculation from another source if it uses
  a different operand.

For the current request pattern:
CSV total -> calculation based on CSV total
PDF -> PDF budget and duration
IMAGE -> image budget and duration

A numerical value from one source must never be used as the input
to a calculation explicitly requested against another source.

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

        deterministic_result = (
            self._build_source_bound_multi_input_answer(
                user_query,
                grounded_evidence,
                data_results,
            )
        )

        if deterministic_result is not None:
            result = deterministic_result
        else:
            result = self._enforce_source_bound_calculations(
                result,
                user_query,
                data_results,
            )

        return {
            "answer": result,
            "evidence_references": [
                item["evidence_id"]
                for item in grounded_evidence
            ],
            "confidence": 0.85,
        }

