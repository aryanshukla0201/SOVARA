from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.execution.broker import ExecutionBroker, ExecutionRequest
from app.evaluation.models import VerificationResult
from app.evaluation.verifier import DeterministicVerifier
from app.planner.models import PlanStep
from app.state.manager import AgentStateManager


@dataclass(frozen=True)
class StepVerificationResult:
    step_id: str
    execution_success: bool
    verification: VerificationResult
    execution_result: dict[str, Any]
    state_updated: bool = False


class ExecutionVerifier:
    """
    P8 integration boundary.

    Executes an existing P4 PlanStep through the existing P5/P7 broker,
    verifies the result deterministically, and records the outcome through
    the existing P6 AgentStateManager.
    """

    def __init__(
        self,
        broker: ExecutionBroker,
        state_manager: AgentStateManager,
        verifier: DeterministicVerifier | None = None,
    ) -> None:
        self.broker = broker
        self.state_manager = state_manager
        self.verifier = verifier or DeterministicVerifier()

    def execute_and_verify(
        self,
        task_id: str,
        step: PlanStep,
        expected_output: Any = None,
        *,
        manage_state: bool = True,
    ) -> StepVerificationResult:
        if manage_state:
            self.state_manager.start_step(task_id, step.step_id)

        request = ExecutionRequest(
            task_id=task_id,
            tool_name=step.tool_name,
            arguments=dict(step.inputs),
        )

        result = self.broker.execute(request)

        if not result.success:
            verification = self.verifier.verify_success(
                False,
                check=f"execution:{step.step_id}",
            )

            self.state_manager.fail_step(
                task_id,
                step.step_id,
                error=result.error or "Execution failed",
                observation={
                    "verification": verification.to_dict(),
                    "execution_result": dict(result.result),
                },
            )

            return StepVerificationResult(
                step_id=step.step_id,
                execution_success=False,
                verification=verification,
                execution_result=dict(result.result),
                state_updated=True,
            )

        if expected_output is None:
            verification = self.verifier.verify_success(
                True,
                check=f"execution:{step.step_id}",
            )
        else:
            verification = self.verifier.verify_output(
                result.result,
                expected_output,
                check=f"output:{step.step_id}",
            )

        if verification.passed:
            self.state_manager.complete_step(
                task_id,
                step.step_id,
                result=dict(result.result),
                observation={
                    "verification": verification.to_dict(),
                },
            )
        else:
            self.state_manager.fail_step(
                task_id,
                step.step_id,
                error=verification.reason,
                observation={
                    "verification": verification.to_dict(),
                    "execution_result": dict(result.result),
                },
            )

        return StepVerificationResult(
            step_id=step.step_id,
            execution_success=True,
            verification=verification,
            execution_result=dict(result.result),
            state_updated=True,
        )
