from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from app.governance.budget import (
    BudgetExceededError,
    ResourceBudget,
    ResourceBudgetGovernor,
)


def test_normal_budget_usage():
    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_tool_calls=2,
            max_llm_calls=2,
        )
    )

    governor.reserve_tool_call()
    governor.reserve_llm_call()

    snapshot = governor.snapshot()

    assert snapshot["usage"]["tool_calls"] == 1
    assert snapshot["usage"]["llm_calls"] == 1


def test_exact_limit_is_allowed():
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_tool_calls=2)
    )

    governor.reserve_tool_call()
    governor.reserve_tool_call()

    assert governor.snapshot()["usage"]["tool_calls"] == 2


def test_over_limit_fails_structured():
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_tool_calls=1)
    )

    governor.reserve_tool_call()

    with pytest.raises(BudgetExceededError) as exc_info:
        governor.reserve_tool_call()

    assert exc_info.value.to_dict() == {
        "error": "budget_exceeded",
        "resource": "tool_calls",
        "limit": 1,
        "current": 1,
        "requested": 1,
    }


def test_multiple_resource_limits_are_independent():
    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_llm_calls=1,
            max_tool_calls=2,
            max_retrieval_calls=3,
        )
    )

    governor.reserve_llm_call()
    governor.reserve_tool_call()
    governor.reserve_tool_call()
    governor.reserve_retrieval_call()

    snapshot = governor.snapshot()

    assert snapshot["usage"]["llm_calls"] == 1
    assert snapshot["usage"]["tool_calls"] == 2
    assert snapshot["usage"]["retrieval_calls"] == 1


def test_parallel_limit_can_be_reserved_and_released():
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_parallel_tasks=2)
    )

    governor.reserve_parallel_task()
    governor.reserve_parallel_task()

    with pytest.raises(BudgetExceededError):
        governor.reserve_parallel_task()

    governor.release_parallel_task()

    governor.reserve_parallel_task()

    assert governor.snapshot()["usage"]["parallel_tasks"] == 2


def test_concurrent_reservation_is_atomic():
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_tool_calls=10)
    )

    def reserve():
        governor.reserve_tool_call()

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [
            pool.submit(reserve)
            for _ in range(20)
        ]

    successes = 0
    failures = 0

    for future in futures:
        try:
            future.result()
            successes += 1
        except BudgetExceededError:
            failures += 1

    assert successes == 10
    assert failures == 10
    assert governor.snapshot()["usage"]["tool_calls"] == 10


def test_token_limits():
    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_context_tokens=100,
            max_generated_tokens=50,
        )
    )

    governor.reserve_context_tokens(80)
    governor.reserve_generated_tokens(40)

    with pytest.raises(BudgetExceededError):
        governor.reserve_context_tokens(21)

    with pytest.raises(BudgetExceededError):
        governor.reserve_generated_tokens(11)


def test_repair_and_retrieval_limits():
    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_repair_attempts=1,
            max_retrieval_calls=1,
        )
    )

    governor.reserve_repair_attempt()
    governor.reserve_retrieval_call()

    with pytest.raises(BudgetExceededError):
        governor.reserve_repair_attempt()

    with pytest.raises(BudgetExceededError):
        governor.reserve_retrieval_call()


def test_negative_budget_rejected():
    with pytest.raises(ValueError):
        ResourceBudget(max_tool_calls=-1)


def test_unknown_resource_rejected():
    governor = ResourceBudgetGovernor(ResourceBudget())

    with pytest.raises(ValueError):
        governor.reserve("unknown_resource")


def test_llm_call_budget_blocks_second_call():
    from unittest.mock import patch

    from app.governance.budget import BudgetExceededError, ResourceBudget, ResourceBudgetGovernor
    from app.models.ollama_adapter import OllamaAdapter

    governor = ResourceBudgetGovernor(
        ResourceBudget(max_llm_calls=1)
    )
    adapter = OllamaAdapter(
        model_name="test-model",
        base_url="http://localhost:11434",
        budget_governor=governor,
    )

    with patch("app.models.ollama_adapter.requests.post") as post:
        response = type("Response", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"response": "ok", "eval_count": 2},
        })()
        post.return_value = response

        assert adapter.generate("hello") == "ok"

        try:
            adapter.generate("second")
            assert False, "Expected LLM budget to be exceeded"
        except BudgetExceededError as exc:
            assert exc.resource == "llm_calls"

        assert post.call_count == 1


def test_generated_token_budget_blocks_before_model_call():
    from unittest.mock import patch

    from app.governance.budget import BudgetExceededError, ResourceBudget, ResourceBudgetGovernor
    from app.models.ollama_adapter import OllamaAdapter

    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_llm_calls=5,
            max_generated_tokens=10,
        )
    )
    adapter = OllamaAdapter(
        model_name="test-model",
        base_url="http://localhost:11434",
        budget_governor=governor,
    )

    with patch("app.models.ollama_adapter.requests.post") as post:
        try:
            adapter.generate("hello", num_predict=11)
            assert False, "Expected generated-token budget to be exceeded"
        except BudgetExceededError as exc:
            assert exc.resource == "generated_tokens"

        assert post.call_count == 0
        assert governor.snapshot()["usage"]["llm_calls"] == 0


def test_generated_tokens_are_recorded_from_actual_usage():
    from unittest.mock import patch

    from app.governance.budget import ResourceBudget, ResourceBudgetGovernor
    from app.models.ollama_adapter import OllamaAdapter

    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_llm_calls=2,
            max_generated_tokens=10,
        )
    )
    adapter = OllamaAdapter(
        model_name="test-model",
        base_url="http://localhost:11434",
        budget_governor=governor,
    )

    with patch("app.models.ollama_adapter.requests.post") as post:
        response = type("Response", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"response": "ok", "eval_count": 4},
        })()
        post.return_value = response

        assert adapter.generate("hello", num_predict=10) == "ok"

    snapshot = governor.snapshot()
    assert snapshot["usage"]["llm_calls"] == 1
    assert snapshot["usage"]["generated_tokens"] == 4


def test_replanner_consumes_repair_budget():
    from unittest.mock import Mock

    from app.governance.budget import (
        BudgetExceededError,
        ResourceBudget,
        ResourceBudgetGovernor,
    )
    from app.planner.models import Plan, PlanStep
    from app.planner.replanner import FailureContext, Replanner

    governor = ResourceBudgetGovernor(
        ResourceBudget(max_repair_attempts=1)
    )

    model = Mock()
    gateway = Mock()
    gateway.resolve.return_value = model

    replanner = Replanner(
        model_gateway=gateway,
        budget_governor=governor,
    )

    plan = Plan(
        task_id="task-repair-budget",
        goal="test replanning",
        steps=[
            PlanStep(
                step_id="s1",
                tool_name="tool",
            )
        ],
    )

    failure = FailureContext(
        failed_step_id="s1",
        failure_reason="test failure",
        attempt=0,
        completed_step_ids=[],
    )

    model.generate_structured.side_effect = RuntimeError(
        "stop after budget reservation"
    )

    with pytest.raises(RuntimeError, match="stop after budget reservation"):
        replanner.replan(plan, failure)

    assert governor.snapshot()["usage"]["repair_attempts"] == 1

    with pytest.raises(BudgetExceededError) as exc_info:
        replanner.replan(plan, failure)

    assert exc_info.value.resource == "repair_attempts"
    assert governor.snapshot()["usage"]["repair_attempts"] == 1



