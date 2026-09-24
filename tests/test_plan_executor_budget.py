from __future__ import annotations

from app.governance.budget import ResourceBudget, ResourceBudgetGovernor
from app.planner.executor import PlanExecutor
from app.planner.models import Plan, PlanStep
from app.governance.audit import AuditEventType
from app.evaluation.models import VerificationStatus


class FakeStateManager:
    def start_task(self, task_id):
        pass

    def complete_task(self, task_id):
        pass

    def fail_task(self, task_id):
        pass

    def start_step(self, task_id, step_id):
        pass

    def complete_step(self, task_id, step_id, result, observation):
        pass

    def fail_step(self, task_id, step_id, error, observation):
        pass


class FakeVerifier:
    def __init__(self):
        self.calls = []

    def execute_and_verify(
        self,
        task_id,
        step,
        expected_output=None,
        *,
        manage_state=True,
    ):
        from app.evaluation.integration import StepVerificationResult
        from app.evaluation.models import VerificationResult, VerificationStatus

        self.calls.append(step.step_id)

        return StepVerificationResult(
            step_id=step.step_id,
            execution_success=True,
            verification=VerificationResult(
                status=VerificationStatus.PASSED,
                check=f"execution:{step.step_id}",
                reason="success",
            ),
            execution_result={"ok": True},
            state_updated=False,
        )


def test_plan_executor_consumes_tool_budget():
    verifier = FakeVerifier()
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_tool_calls=2)
    )

    executor = PlanExecutor(
        verifier=verifier,
        state_manager=FakeStateManager(),
        budget_governor=governor,
    )

    plan = Plan(
        task_id="task-budget",
        goal="test",
        steps=[
            PlanStep(step_id="s1", tool_name="tool"),
            PlanStep(step_id="s2", tool_name="tool"),
        ],
    )

    result = executor.execute(plan)

    assert result.status.value == "completed"
    assert verifier.calls == ["s1", "s2"]
    assert governor.snapshot()["usage"]["tool_calls"] == 2


def test_plan_executor_blocks_step_when_tool_budget_exhausted():
    verifier = FakeVerifier()
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_tool_calls=1)
    )

    executor = PlanExecutor(
        verifier=verifier,
        state_manager=FakeStateManager(),
        budget_governor=governor,
    )

    plan = Plan(
        task_id="task-budget",
        goal="test",
        steps=[
            PlanStep(step_id="s1", tool_name="tool"),
            PlanStep(step_id="s2", tool_name="tool"),
        ],
    )

    result = executor.execute(plan)

    assert result.status.value == "failed"
    assert verifier.calls == ["s1"]

    assert result.step_results["s2"].execution_success is False
    assert result.step_results["s2"].verification.details[
        "error"
    ] == "budget_exceeded"

    assert governor.snapshot()["usage"]["tool_calls"] == 1

def test_parallel_steps_respect_parallel_budget():
    import threading
    import time

    from app.evaluation.integration import StepVerificationResult
    from app.evaluation.models import VerificationResult, VerificationStatus

    class BlockingVerifier(FakeVerifier):
        def execute_and_verify(
            self,
            task_id,
            step,
            expected_output=None,
            *,
            manage_state=True,
        ):
            self.calls.append(step.step_id)

            time.sleep(0.1)

            return StepVerificationResult(
                step_id=step.step_id,
                execution_success=True,
                verification=VerificationResult(
                    status=VerificationStatus.PASSED,
                    check=f"execution:{step.step_id}",
                    reason="success",
                ),
                execution_result={"ok": True},
                state_updated=False,
            )

    verifier = BlockingVerifier()

    governor = ResourceBudgetGovernor(
        ResourceBudget(
            max_tool_calls=4,
            max_parallel_tasks=2,
        )
    )

    executor = PlanExecutor(
        verifier=verifier,
        state_manager=FakeStateManager(),
        max_workers=4,
        budget_governor=governor,
    )

    plan = Plan(
        task_id="task-parallel-budget",
        goal="parallel budget test",
        steps=[
            PlanStep(step_id="s1", tool_name="tool"),
            PlanStep(step_id="s2", tool_name="tool"),
            PlanStep(step_id="s3", tool_name="tool"),
            PlanStep(step_id="s4", tool_name="tool"),
        ],
    )

    result = executor.execute(plan)

    assert result.status.value == "completed"
    assert len(verifier.calls) == 4
    assert governor.snapshot()["usage"]["tool_calls"] == 4
    assert governor.snapshot()["usage"]["parallel_tasks"] == 0

def test_budget_exceeded_is_recorded_in_existing_observability():
    from app.governance.observability import Observability

    governor = ResourceBudgetGovernor(
        ResourceBudget(max_tool_calls=0)
    )

    observability = Observability()

    executor = PlanExecutor(
        verifier=FakeVerifier(),
        state_manager=FakeStateManager(),
        budget_governor=governor,
        observability=observability,
    )

    plan = Plan(
        task_id="task-budget-audit",
        goal="budget audit test",
        steps=[
            PlanStep(
                step_id="s1",
                tool_name="tool",
            )
        ],
    )

    result = executor.execute(plan)

    assert result.status.value == "failed"

    events = observability.get_events("task-budget-audit")

    assert len(events) == 1
    assert events[0].event_type == AuditEventType.BUDGET_EXCEEDED
    assert events[0].decision == "denied"
    assert events[0].metadata["resource"] == "tool_calls"





def test_execution_time_budget_exceeded_before_scheduling():
    governor = ResourceBudgetGovernor(
        ResourceBudget(max_execution_time_ms=0)
    )

    executor = PlanExecutor(
        verifier=FakeVerifier(),
        state_manager=FakeStateManager(),
        budget_governor=governor,
    )

    plan = Plan(
        task_id="task-budget-time",
        goal="execution time budget test",
        steps=[
            PlanStep(
                step_id="s1",
                tool_name="tool",
            )
        ],
    )

    result = executor.execute(plan)

    assert result.status.value == "failed"
    assert result.step_results["s1"].verification.status == VerificationStatus.FAILED
    assert result.step_results["s1"].verification.reason.startswith(
        "Budget exceeded for execution_time_ms"
    )


def test_execution_time_budget_is_checked_after_running_step():
    import time

    class SlowVerifier(FakeVerifier):
        def execute_and_verify(
            self,
            task_id,
            step,
            expected_output=None,
            *,
            manage_state=True,
        ):
            time.sleep(0.02)
            return super().execute_and_verify(
                task_id,
                step,
                expected_output,
                manage_state=manage_state,
            )

    governor = ResourceBudgetGovernor(
        ResourceBudget(max_execution_time_ms=1)
    )

    executor = PlanExecutor(
        verifier=SlowVerifier(),
        state_manager=FakeStateManager(),
        budget_governor=governor,
    )

    plan = Plan(
        task_id="task-budget-time-after",
        goal="execution time after running test",
        steps=[
            PlanStep(
                step_id="s1",
                tool_name="tool",
            )
        ],
    )

    result = executor.execute(plan)

    assert result.status.value == "failed"
    assert result.step_results["s1"].verification.status == VerificationStatus.FAILED
    assert result.step_results["s1"].verification.reason.startswith(
        "Budget exceeded for execution_time_ms"
    )



