from __future__ import annotations

import threading
import time

from app.evaluation.integration import ExecutionVerifier
from app.execution.broker import ExecutionResult
from app.planner.executor import PlanExecutor
from app.planner.models import Plan, PlanStep
from app.state.manager import AgentStateManager
from app.state.store import DurableStateStore


class FakeBroker:
    def __init__(self, results=None, barrier=None):
        self.results = results or {}
        self.barrier = barrier
        self.calls = []
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def execute(self, request):
        with self.lock:
            self.calls.append(request.tool_name)
            self.active += 1
            self.max_active = max(self.max_active, self.active)

        try:
            if self.barrier is not None:
                self.barrier.wait(timeout=3)

            time.sleep(0.05)

            return self.results.get(
                request.tool_name,
                ExecutionResult(
                    tool_name=request.tool_name,
                    success=True,
                    result={"tool": request.tool_name},
                ),
            )
        finally:
            with self.lock:
                self.active -= 1


class FakeStateManager:
    def __init__(self):
        self.calls = []
        self.tasks = {
            "task-1": object(),
        }

    def require_task(self, task_id):
        return self.tasks[task_id]

    def start_task(self, task_id):
        self.calls.append(("start_task", task_id))

    def start_step(self, task_id, step_id):
        self.calls.append(("start", step_id))

    def complete_step(
        self,
        task_id,
        step_id,
        result,
        observation=None,
    ):
        self.calls.append(("complete", step_id))

    def fail_step(
        self,
        task_id,
        step_id,
        error,
        observation=None,
    ):
        self.calls.append(("fail", step_id))

    def fail_task(self, task_id):
        self.calls.append(("fail_task", task_id))

    def complete_task(self, task_id):
        self.calls.append(("complete_task", task_id))


def make_plan(steps):
    return Plan(
        goal="test",
        task_id="task-1",
        steps=steps,
    )


def make_executor(broker, state):
    return PlanExecutor(
        verifier=ExecutionVerifier(
            broker,
            state,
        ),
        state_manager=state,
        max_workers=3,
    )


def test_independent_steps_execute_in_parallel():
    barrier = threading.Barrier(3)
    broker = FakeBroker(barrier=barrier)
    state = FakeStateManager()

    plan = make_plan(
        [
            PlanStep("a", "A"),
            PlanStep("b", "B"),
            PlanStep("c", "C"),
        ]
    )

    result = make_executor(broker, state).execute(plan)

    assert result.status.value == "completed"
    assert set(result.step_results) == {"a", "b", "c"}
    assert broker.max_active == 3


def test_dependency_waits_for_all_parents():
    events = []
    lock = threading.Lock()

    class OrderedBroker(FakeBroker):
        def execute(self, request):
            with lock:
                events.append(("start", request.tool_name))

            time.sleep(0.02)

            with lock:
                events.append(("finish", request.tool_name))

            return ExecutionResult(
                tool_name=request.tool_name,
                success=True,
                result={"ok": True},
            )

    broker = OrderedBroker()
    state = FakeStateManager()

    plan = make_plan(
        [
            PlanStep("a", "A"),
            PlanStep("b", "B"),
            PlanStep("c", "C", depends_on=["a", "b"]),
        ]
    )

    result = make_executor(broker, state).execute(plan)

    assert result.status.value == "completed"

    c_start = events.index(("start", "C"))
    assert events.index(("finish", "A")) < c_start
    assert events.index(("finish", "B")) < c_start


def test_failed_dependency_skips_dependent():
    broker = FakeBroker(
        results={
            "A": ExecutionResult(
                tool_name="A",
                success=False,
                result={},
                error="failed",
            )
        }
    )
    state = FakeStateManager()

    plan = make_plan(
        [
            PlanStep("a", "A"),
            PlanStep("b", "B", depends_on=["a"]),
        ]
    )

    result = make_executor(broker, state).execute(plan)

    assert result.status.value == "failed"
    assert "b" in result.skipped_steps
    assert "B" not in broker.calls


def test_sequential_plan_remains_sequential():
    broker = FakeBroker()
    state = FakeStateManager()

    plan = make_plan(
        [
            PlanStep("a", "A"),
            PlanStep("b", "B", depends_on=["a"]),
            PlanStep("c", "C", depends_on=["b"]),
        ]
    )

    result = make_executor(broker, state).execute(plan)

    assert result.status.value == "completed"
    assert broker.calls == ["A", "B", "C"]
    assert broker.max_active == 1


def test_parallel_execution_respects_worker_bound():
    broker = FakeBroker()
    state = FakeStateManager()

    plan = make_plan(
        [
            PlanStep("a", "A"),
            PlanStep("b", "B"),
        ]
    )

    result = PlanExecutor(
        verifier=ExecutionVerifier(broker, state),
        state_manager=state,
        max_workers=1,
    ).execute(plan)

    assert result.status.value == "completed"
    assert broker.calls == ["A", "B"]
    assert broker.max_active == 1
