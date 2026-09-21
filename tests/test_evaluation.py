from app.evaluation.models import (
    EvaluationCase,
    EvaluationResult,
    EvaluationSummary,
    VerificationResult,
    VerificationStatus,
)
from app.evaluation.suite import EvaluationSuite
from app.evaluation.verifier import DeterministicVerifier


def test_verification_result_serialization_round_trip():
    result = VerificationResult(
        status=VerificationStatus.PASSED,
        check="output_match",
        reason="match",
        details={"value": 42},
    )

    restored = VerificationResult.from_dict(result.to_dict())

    assert restored == result
    assert restored.passed


def test_deterministic_verifier_passes_matching_output():
    verifier = DeterministicVerifier()

    result = verifier.verify_output({"value": 42}, {"value": 42})

    assert result.passed
    assert result.status == VerificationStatus.PASSED


def test_deterministic_verifier_rejects_mismatched_output():
    verifier = DeterministicVerifier()

    result = verifier.verify_output({"value": 42}, {"value": 43})

    assert not result.passed
    assert result.status == VerificationStatus.FAILED
    assert result.details["expected"] == {"value": 43}
    assert result.details["actual"] == {"value": 42}


def test_success_verification():
    verifier = DeterministicVerifier()

    assert verifier.verify_success(True).passed
    assert not verifier.verify_success(False).passed


def test_required_fields_verification():
    verifier = DeterministicVerifier()

    passed = verifier.verify_required_fields(
        {"task_id": "t1", "status": "completed"},
        ["task_id", "status"],
    )
    failed = verifier.verify_required_fields(
        {"task_id": "t1"},
        ["task_id", "status"],
    )

    assert passed.passed
    assert not failed.passed
    assert failed.details["missing_fields"] == ["status"]


def test_evaluation_case_serialization_round_trip():
    case = EvaluationCase(
        case_id="case-1",
        name="addition",
        input_data={"a": 2, "b": 3},
        expected_output=5,
        metadata={"category": "deterministic"},
    )

    restored = EvaluationCase.from_dict(case.to_dict())

    assert restored == case


def test_evaluation_suite_passes_all_cases():
    suite = EvaluationSuite()
    cases = [
        EvaluationCase("case-1", "two plus three", {"a": 2, "b": 3}, 5),
        EvaluationCase("case-2", "four plus six", {"a": 4, "b": 6}, 10),
    ]

    summary = suite.evaluate(
        cases,
        lambda data: data["a"] + data["b"],
    )

    assert summary.total == 2
    assert summary.passed == 2
    assert summary.failed == 0
    assert summary.success


def test_evaluation_suite_reports_failed_case():
    suite = EvaluationSuite()
    cases = [
        EvaluationCase("case-1", "correct", {"value": 5}, 5),
        EvaluationCase("case-2", "incorrect", {"value": 6}, 7),
    ]

    summary = suite.evaluate(
        cases,
        lambda data: data["value"],
    )

    assert summary.total == 2
    assert summary.passed == 1
    assert summary.failed == 1
    assert not summary.success
    assert summary.results[1].case_id == "case-2"


def test_evaluation_suite_contains_evaluator_errors_as_failures():
    suite = EvaluationSuite()
    cases = [EvaluationCase("case-1", "raises", {}, 1)]

    def evaluator(_data):
        raise RuntimeError("boom")

    summary = suite.evaluate(cases, evaluator)

    assert summary.total == 1
    assert summary.passed == 0
    assert summary.failed == 1
    assert "RuntimeError" in summary.results[0].reason


def test_evaluation_is_deterministic_for_same_inputs():
    suite = EvaluationSuite()
    cases = [
        EvaluationCase("case-1", "multiply", {"a": 7, "b": 6}, 42),
    ]

    evaluator = lambda data: data["a"] * data["b"]

    first = suite.evaluate(cases, evaluator).to_dict()
    second = suite.evaluate(cases, evaluator).to_dict()

    assert first == second


def test_evaluation_summary_serialization_shape():
    result = EvaluationResult(
        case_id="case-1",
        passed=True,
        actual_output=5,
        expected_output=5,
        reason="actual output matches expected output",
    )
    summary = EvaluationSummary(
        total=1,
        passed=1,
        failed=0,
        results=(result,),
    )

    data = summary.to_dict()

    assert data["total"] == 1
    assert data["passed"] == 1
    assert data["failed"] == 0
    assert data["results"][0]["case_id"] == "case-1"
