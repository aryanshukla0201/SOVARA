from __future__ import annotations


PLANNER_MAX_TOKENS = 768

SIMPLE_MAX_TOKENS = 512
REASONING_MAX_TOKENS = 1024
COMPLEX_MAX_TOKENS = 1536

REPAIR_MAX_TOKENS = 1024
DEFAULT_MAX_TOKENS = 1024


def get_response_budget(
    *,
    complexity: str | None = None,
    task_type: str | None = None,
) -> int:
    normalized_complexity = (complexity or "").strip().lower()
    normalized_task = (task_type or "").strip().lower()

    if normalized_task in {"planner", "planning"}:
        return PLANNER_MAX_TOKENS

    if normalized_task in {"repair", "fix"}:
        return REPAIR_MAX_TOKENS

    if normalized_complexity in {"simple", "low"}:
        return SIMPLE_MAX_TOKENS

    if normalized_complexity in {"complex", "high"}:
        return COMPLEX_MAX_TOKENS

    return REASONING_MAX_TOKENS


def get_reasoning_budget(
    *,
    evidence_count: int = 0,
    data_result_count: int = 0,
    code_result_count: int = 0,
    vision_result_count: int = 0,
) -> int:
    """
    Derive the reasoning generation budget from already-known execution
    evidence. No additional LLM classification is performed.

    This mirrors the existing complexity-gate principle:
    - multiple result modalities -> complex
    - retrieved evidence -> grounded synthesis-style reasoning
    - multiple data/code results -> complex
    - otherwise -> normal/simple reasoning
    """
    modality_count = sum(
        [
            evidence_count > 0,
            data_result_count > 0,
            code_result_count > 0,
            vision_result_count > 0,
        ]
    )

    if modality_count >= 2:
        return COMPLEX_MAX_TOKENS

    if evidence_count > 0:
        return COMPLEX_MAX_TOKENS

    if data_result_count > 1 or code_result_count > 1:
        return COMPLEX_MAX_TOKENS

    if (
        data_result_count == 1
        or code_result_count == 1
        or vision_result_count == 1
    ):
        return REASONING_MAX_TOKENS

    return SIMPLE_MAX_TOKENS
