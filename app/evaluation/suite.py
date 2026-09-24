from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from app.evaluation.models import EvaluationCase, EvaluationResult, EvaluationSummary
from app.evaluation.verifier import DeterministicVerifier


class EvaluationSuite:
    """Runs deterministic evaluation cases without mutating application state."""

    def __init__(self, verifier: DeterministicVerifier | None = None) -> None:
        self.verifier = verifier or DeterministicVerifier()

    def evaluate_case(
        self,
        case: EvaluationCase,
        evaluator: Callable[[dict[str, Any]], Any],
    ) -> EvaluationResult:
        try:
            actual = evaluator(dict(case.input_data))
        except Exception as exc:
            return EvaluationResult(
                case_id=case.case_id,
                passed=False,
                expected_output=case.expected_output,
                reason=f"evaluation raised {type(exc).__name__}: {exc}",
            )

        verification = self.verifier.verify(
            actual,
            case.expected_output,
            check=f"evaluation:{case.case_id}",
        )

        return EvaluationResult(
            case_id=case.case_id,
            passed=verification.passed,
            actual_output=actual,
            expected_output=case.expected_output,
            reason=verification.reason,
        )

    def evaluate(
        self,
        cases: Iterable[EvaluationCase],
        evaluator: Callable[[dict[str, Any]], Any],
    ) -> EvaluationSummary:
        results = tuple(self.evaluate_case(case, evaluator) for case in cases)
        passed = sum(1 for result in results if result.passed)

        return EvaluationSummary(
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            results=results,
        )
