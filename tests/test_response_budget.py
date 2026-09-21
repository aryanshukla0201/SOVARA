from app.models.response_budget import (
    COMPLEX_MAX_TOKENS,
    REASONING_MAX_TOKENS,
    SIMPLE_MAX_TOKENS,
    get_reasoning_budget,
)


def test_empty_reasoning_is_simple():
    assert get_reasoning_budget() == SIMPLE_MAX_TOKENS


def test_single_data_result_uses_normal_reasoning_budget():
    assert (
        get_reasoning_budget(data_result_count=1)
        == REASONING_MAX_TOKENS
    )


def test_grounded_evidence_uses_complex_budget():
    assert (
        get_reasoning_budget(evidence_count=1)
        == COMPLEX_MAX_TOKENS
    )


def test_multiple_modalities_use_complex_budget():
    assert (
        get_reasoning_budget(
            data_result_count=1,
            vision_result_count=1,
        )
        == COMPLEX_MAX_TOKENS
    )


def test_multiple_data_results_use_complex_budget():
    assert (
        get_reasoning_budget(data_result_count=2)
        == COMPLEX_MAX_TOKENS
    )


def test_multiple_code_results_use_complex_budget():
    assert (
        get_reasoning_budget(code_result_count=2)
        == COMPLEX_MAX_TOKENS
    )
