from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any

from app.evaluation.integration import ExecutionVerifier, StepVerificationResult
from app.governance.audit import AuditEvent, AuditEventType
from app.governance.budget import BudgetExceededError, ResourceBudgetGovernor
from app.governance.observability import Observability
from app.evaluation.models import VerificationResult, VerificationStatus
from app.planner.models import Plan, PlanStep, PlanStepStatus, PlanStatus
from app.planner.validator import PlanValidator
from app.state.manager import AgentStateManager
from app.state.models import TaskStatus
from app.services.run_trace import RunTrace
from app.state.execution_event_projection import project_run_trace_events


@dataclass
class PlanExecutionResult:
    plan_id: str
    task_id: str
    status: PlanStatus
    step_results: dict[str, StepVerificationResult] = field(default_factory=dict)
    skipped_steps: list[str] = field(default_factory=list)
    execution_events: list[dict[str, Any]] = field(default_factory=list)


class PlanExecutor:
    """
    Dependency-aware DAG executor.

    Parallelism is applied only to independent plan steps.
    Every actual tool execution remains inside ExecutionVerifier -> ExecutionBroker.
    Durable P6 state transitions are serialized to preserve optimistic versioning.
    """

    def __init__(
        self,
        verifier: ExecutionVerifier,
        state_manager: AgentStateManager,
        validator: PlanValidator | None = None,
        max_workers: int = 4,
        budget_governor: ResourceBudgetGovernor | None = None,
        observability: Observability | None = None,
        run_trace: RunTrace | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")

        self.verifier = verifier
        self.state_manager = state_manager
        self.validator = validator
        self.max_workers = max_workers
        self.budget_governor = budget_governor
        self.observability = observability
        self.run_trace = run_trace

    def execute(
        self,
        plan: Plan,
        *,
        expected_outputs: dict[str, Any] | None = None,
    ) -> PlanExecutionResult:
        self._validate(plan)

        task_id = plan.task_id
        if not task_id.strip():
            raise ValueError("Plan task_id must not be empty")

        plan.status = PlanStatus.RUNNING
        self.state_manager.start_task(task_id)

        trace_id = None
        if self.run_trace is not None:
            trace_id = self.run_trace.start_run(
                task_id,
                plan.plan_id,
            )

        expected_outputs = expected_outputs or {}
        step_by_id = {step.step_id: step for step in plan.steps}

        completed: set[str] = set()
        failed: set[str] = set()
        skipped: set[str] = set()
        results: dict[str, StepVerificationResult] = {}

        pending = set(step_by_id)

        with ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="sovara-plan",
        ) as pool:
            futures: dict[Future[StepVerificationResult], PlanStep] = {}

            while pending or futures:
                cancelled = self._is_cancelled(task_id)

                if cancelled:
                    for step_id in sorted(pending):
                        step = step_by_id[step_id]
                        step.status = PlanStepStatus.SKIPPED
                        skipped.add(step_id)

                    pending.clear()
                self._mark_blocked_steps(
                    pending=pending,
                    step_by_id=step_by_id,
                    completed=completed,
                    failed=failed,
                    skipped=skipped,
                )

                # Schedule each currently-ready step exactly once.
                for step_id in sorted(list(pending)):
                    if self._is_cancelled(task_id):
                        for remaining_id in sorted(pending):
                            remaining_step = step_by_id[remaining_id]
                            remaining_step.status = PlanStepStatus.SKIPPED
                            skipped.add(remaining_id)
                        pending.clear()
                        break
                    step = step_by_id[step_id]

                    if not self._dependencies_satisfied(
                        step,
                        completed,
                    ):
                        continue

                    if self.budget_governor is not None:
                        try:
                            self.budget_governor.check_execution_time()

                            # Parallel-task budget is a concurrency limit.
                            # If all slots are occupied, leave this step
                            # pending and retry after a running task completes.
                            self.budget_governor.reserve_parallel_task()

                            try:
                                self.budget_governor.reserve_tool_call()
                            except BudgetExceededError:
                                self.budget_governor.release_parallel_task()
                                raise

                        except BudgetExceededError as exc:
                            if exc.resource == "parallel_tasks":
                                continue

                            if self.observability is not None:
                                self.observability.record(
                                    AuditEvent.create(
                                        event_id=f"budget-{task_id}-{step.step_id}",
                                        task_id=task_id,
                                        event_type=AuditEventType.BUDGET_EXCEEDED,
                                        tool_name=step.tool_name,
                                        action="budget_reservation",
                                        decision="denied",
                                        reason=str(exc),
                                        metadata=exc.to_dict(),
                                    )
                                )

                            result = self._budget_exception_result(
                                step,
                                exc,
                            )
                            results[step.step_id] = result

                            step.status = PlanStepStatus.FAILED
                            failed.add(step.step_id)

                            self.state_manager.fail_step(
                                task_id,
                                step.step_id,
                                error=result.verification.reason,
                                observation={
                                    "verification": result.verification.to_dict(),
                                    "budget": exc.to_dict(),
                                },
                            )
                            pending.remove(step_id)
                            continue
                    self.state_manager.start_step(
                        task_id,
                        step.step_id,
                    )
                    step.status = PlanStepStatus.RUNNING
                    pending.remove(step_id)

                    if self.run_trace is not None:
                        self.run_trace.record_step_started(
                            trace_id,
                            step.step_id,
                            step.tool_name,
                            metadata={
                                "depends_on": list(step.depends_on),
                            },
                        )

                    future = pool.submit(
                        self.verifier.execute_and_verify,
                        task_id,
                        step,
                        expected_outputs.get(step.step_id),
                        manage_state=False,
                    )
                    futures[future] = step

                if not futures:
                    if pending:
                        raise RuntimeError(
                            "Planner execution made no progress; "
                            "dependency state is inconsistent."
                        )
                    break

                done_future = next(as_completed(futures))
                step = futures.pop(done_future)

                try:
                    result = done_future.result()
                except Exception as exc:
                    result = self._execution_exception_result(
                        step,
                        exc,
                    )

                if self.budget_governor is not None:
                    self.budget_governor.release_parallel_task()

                    try:
                        self.budget_governor.check_execution_time()
                    except BudgetExceededError as exc:
                        if self.observability is not None:
                            self.observability.record(
                                AuditEvent.create(
                                    event_id=f"budget-{task_id}-{step.step_id}",
                                    task_id=task_id,
                                    event_type=AuditEventType.BUDGET_EXCEEDED,
                                    tool_name=step.tool_name,
                                    action="budget_check",
                                    decision="denied",
                                    reason=str(exc),
                                    metadata=exc.to_dict(),
                                )
                            )

                        result = self._budget_exception_result(
                            step,
                            exc,
                        )
                        step.status = PlanStepStatus.FAILED
                        failed.add(step.step_id)

                results[step.step_id] = result

                cancelled_after_execution = self._is_cancelled(task_id)

                if cancelled_after_execution:
                    if result.verification.passed:
                        step.status = PlanStepStatus.COMPLETED
                        completed.add(step.step_id)
                    else:
                        step.status = PlanStepStatus.FAILED
                        failed.add(step.step_id)

                    continue

                if self.run_trace is not None:
                    if result.verification.passed:
                        self.run_trace.record_step_completed(
                            trace_id,
                            step.step_id,
                            step.tool_name,
                            metadata={
                                "verification": (
                                    result.verification.to_dict()
                                ),
                            },
                        )
                    else:
                        self.run_trace.record_step_failed(
                            trace_id,
                            step.step_id,
                            step.tool_name,
                            error=result.verification.reason,
                            metadata={
                                "verification": (
                                    result.verification.to_dict()
                                ),
                            },
                        )

                if result.verification.passed:
                    step.status = PlanStepStatus.COMPLETED
                    completed.add(step.step_id)

                    self.state_manager.complete_step(
                        task_id,
                        step.step_id,
                        result=dict(result.execution_result),
                        observation={
                            "verification": result.verification.to_dict(),
                        },
                    )
                else:
                    step.status = PlanStepStatus.FAILED
                    failed.add(step.step_id)

                    self.state_manager.fail_step(
                        task_id,
                        step.step_id,
                        error=result.verification.reason,
                        observation={
                            "verification": result.verification.to_dict(),
                            "execution_result": dict(
                                result.execution_result
                            ),
                        },
                    )

        if self._is_cancelled(task_id):
            plan.status = PlanStatus.CANCELLED
        elif failed:
            plan.status = PlanStatus.FAILED
            self.state_manager.fail_task(task_id)
        else:
            plan.status = PlanStatus.COMPLETED
            self.state_manager.complete_task(task_id)

        if self.run_trace is not None:
            self.run_trace.finish_run(
                trace_id,
                plan.status.value,
            )

        execution_events: list[dict[str, Any]] = []

        if self.run_trace is not None and trace_id is not None:
            execution_events = [
                asdict(event)
                for event in project_run_trace_events(
                    self.run_trace.get_events(trace_id),
                )
            ]

        return PlanExecutionResult(
            plan_id=plan.plan_id,
            task_id=task_id,
            status=plan.status,
            step_results=results,
            skipped_steps=sorted(skipped),
            execution_events=execution_events,
        )

    def _is_cancelled(self, task_id: str) -> bool:
        require_task = getattr(self.state_manager, "require_task", None)
        if require_task is None:
            return False

        try:
            task = require_task(task_id)
        except KeyError:
            return False

        return getattr(task, "status", None) == TaskStatus.CANCELLED

    def _validate(self, plan: Plan) -> None:
        if self.validator is not None:
            self.validator.validate(plan).raise_if_invalid()

    @staticmethod
    def _dependencies_satisfied(
        step: PlanStep,
        completed: set[str],
    ) -> bool:
        return all(
            dependency in completed
            for dependency in step.depends_on
        )

    @staticmethod
    def _mark_blocked_steps(
        *,
        pending: set[str],
        step_by_id: dict[str, PlanStep],
        completed: set[str],
        failed: set[str],
        skipped: set[str],
    ) -> None:
        for step_id in sorted(pending):
            step = step_by_id[step_id]

            if any(
                dependency in failed or dependency in skipped
                for dependency in step.depends_on
            ):
                step.status = PlanStepStatus.SKIPPED
                skipped.add(step_id)
                pending.remove(step_id)

    @staticmethod
    def _budget_exception_result(
        step: PlanStep,
        exc: BudgetExceededError,
    ) -> StepVerificationResult:
        verification = VerificationResult(
            status=VerificationStatus.FAILED,
            check=f"budget:{step.step_id}",
            reason=str(exc),
            details=exc.to_dict(),
        )

        return StepVerificationResult(
            step_id=step.step_id,
            execution_success=False,
            verification=verification,
            execution_result={
                "error": str(exc),
                "budget": exc.to_dict(),
            },
            state_updated=False,
        )

    @staticmethod
    def _execution_exception_result(
        step: PlanStep,
        exc: Exception,
    ) -> StepVerificationResult:
        verification = VerificationResult(
            status=VerificationStatus.FAILED,
            check=f"execution:{step.step_id}",
            reason=f"Execution exception: {exc}",
            details={"exception_type": type(exc).__name__},
        )

        return StepVerificationResult(
            step_id=step.step_id,
            execution_success=False,
            verification=verification,
            execution_result={
                "error": str(exc),
            },
            state_updated=False,
        )
