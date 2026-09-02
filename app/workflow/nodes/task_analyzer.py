from __future__ import annotations

from app.models.model_factory import ModelFactory
from app.state.task_state import TaskState


class TaskAnalyzer:
    """
    Determines the user's task intent using the LLM, then normalizes
    the workflow configuration deterministically based on the actual
    detected input types.

    The LLM is not trusted to decide technical routing flags such as
    whether vision is required for a PDF.
    """

    VALID_MODEL_CAPABILITIES = {
        "reasoning",
        "summarization",
        "document_analysis",
        "data_analysis",
        "vision_analysis",
        "code",
        "general",
    }

    def __init__(self, model=None):
        self.model = model or ModelFactory.create("qwen")

    def analyze(
        self,
        user_query: str,
        input_types: list[str],
    ) -> TaskState:

        # ---------------------------------------------------------
        # NORMALIZE INPUT TYPES
        # ---------------------------------------------------------

        input_types = [
            str(input_type).lower().strip()
            for input_type in (input_types or [])
        ]

        # ---------------------------------------------------------
        # ASK MODEL FOR SEMANTIC TASK UNDERSTANDING
        # ---------------------------------------------------------

        prompt = f"""
You are a task classification component.

Analyze the user's request and return STRICT JSON only.

User request:
{user_query}

Available input types:
{input_types}

Return exactly these keys:

intent
required_capabilities
recommended_model_capability
output_format
deliverable

Rules:

- intent must be a short snake_case label.
- required_capabilities must be a JSON list of strings.
- recommended_model_capability must be ONE string only, never a list.
- Choose recommended_model_capability from:
  reasoning,
  summarization,
  document_analysis,
  data_analysis,
  vision_analysis,
  code,
  general

Do not include routing flags such as requires_vision,
requires_rag, requires_tools, or requires_synthesis.
Those are determined separately by the application.

Example:

{{
    "intent": "document_summary",
    "required_capabilities": [
        "summarization",
        "reasoning"
    ],
    "recommended_model_capability": "summarization",
    "output_format": "text",
    "deliverable": "summary"
}}
"""

        try:
            payload = self.model.generate_structured(
                prompt,
                schema={},
            )
        except Exception:
            payload = {}

        # ---------------------------------------------------------
        # FALLBACK
        # ---------------------------------------------------------

        if not isinstance(payload, dict):
            payload = {}

        intent = payload.get(
            "intent",
            "general_analysis",
        )

        if not isinstance(intent, str) or not intent.strip():
            intent = "general_analysis"

        intent = intent.strip().lower().replace(" ", "_")

        # ---------------------------------------------------------
        # NORMALIZE MODEL CAPABILITY
        # ---------------------------------------------------------

        recommended_model_capability = payload.get(
            "recommended_model_capability",
            "reasoning",
        )

        # Sometimes the LLM incorrectly returns a list.
        if isinstance(recommended_model_capability, list):

            recommended_model_capability = (
                recommended_model_capability[0]
                if recommended_model_capability
                else "reasoning"
            )

        if not isinstance(recommended_model_capability, str):

            recommended_model_capability = "reasoning"

        recommended_model_capability = (
            recommended_model_capability
            .strip()
            .lower()
        )

        if (
            recommended_model_capability
            not in self.VALID_MODEL_CAPABILITIES
        ):
            recommended_model_capability = "reasoning"

        # ---------------------------------------------------------
        # NORMALIZE REQUIRED CAPABILITIES
        # ---------------------------------------------------------

        capabilities = payload.get(
            "required_capabilities",
            [],
        )

        if not isinstance(capabilities, list):

            if isinstance(capabilities, str):
                capabilities = [capabilities]
            else:
                capabilities = []

        capabilities = [
            str(capability).strip().lower()
            for capability in capabilities
            if str(capability).strip()
        ]

        # ---------------------------------------------------------
        # INPUT-DRIVEN ROUTING
        # ---------------------------------------------------------

        has_pdf = "pdf" in input_types
        has_docx = "docx" in input_types

        has_document = (
            has_pdf
            or has_docx
        )

        has_csv = "csv" in input_types
        has_xlsx = "xlsx" in input_types

        has_data = (
            has_csv
            or has_xlsx
        )

        has_image = "image" in input_types

        # ---------------------------------------------------------
        # DOCUMENT INPUT
        # ---------------------------------------------------------

        if has_document:

            if "document_analysis" not in capabilities:
                capabilities.append(
                    "document_analysis"
                )

        # ---------------------------------------------------------
        # DATA INPUT
        # ---------------------------------------------------------

        if has_data:

            if "data_analysis" not in capabilities:
                capabilities.append(
                    "data_analysis"
                )

        # ---------------------------------------------------------
        # IMAGE INPUT
        # ---------------------------------------------------------

        if has_image:

            if "vision_analysis" not in capabilities:
                capabilities.append(
                    "vision_analysis"
                )

        # ---------------------------------------------------------
        # REASONING
        # ---------------------------------------------------------

        if "reasoning" not in capabilities:
            capabilities.append("reasoning")

        # ---------------------------------------------------------
        # REMOVE DUPLICATES
        # ---------------------------------------------------------

        capabilities = list(
            dict.fromkeys(capabilities)
        )

        # ---------------------------------------------------------
        # DETERMINISTIC ROUTING FLAGS
        # ---------------------------------------------------------

        requires_vision = has_image

        requires_rag = has_document

        requires_code = (
            "code" in capabilities
        )

        requires_tools = (
            has_document
            or has_data
            or has_image
        )

        execution_routes = 0

        if has_document:
            execution_routes += 1

        if has_data:
            execution_routes += 1

        if has_image:
            execution_routes += 1

        requires_synthesis = (
            execution_routes > 1
        )

        # ---------------------------------------------------------
        # OUTPUT FORMAT
        # ---------------------------------------------------------

        output_format = payload.get(
            "output_format",
            "text",
        )

        if (
            not isinstance(output_format, str)
            or not output_format.strip()
        ):
            output_format = "text"

        output_format = output_format.strip().lower()

        # ---------------------------------------------------------
        # DELIVERABLE
        # ---------------------------------------------------------

        deliverable = payload.get(
            "deliverable",
            "answer",
        )

        if (
            not isinstance(deliverable, str)
            or not deliverable.strip()
        ):
            deliverable = "answer"

        deliverable = deliverable.strip()

        # ---------------------------------------------------------
        # CREATE CLEAN TASK STATE
        # ---------------------------------------------------------

        clean_payload = {
            "intent": intent,

            "required_capabilities": capabilities,

            "requires_vision": requires_vision,

            "requires_rag": requires_rag,

            "requires_code": requires_code,

            "requires_tools": requires_tools,

            "requires_synthesis": requires_synthesis,

            "recommended_model_capability":
                recommended_model_capability,

            "output_format": output_format,

            "deliverable": deliverable,
        }

        task = TaskState.model_validate(
            clean_payload
        )

        # ---------------------------------------------------------
        # POST-PROCESS STATE
        # ---------------------------------------------------------

        task.detected_input_types = input_types

        task.task_type = intent

        return task