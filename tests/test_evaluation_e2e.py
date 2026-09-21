from app.evaluation.integration import ExecutionVerifier
from app.evaluation.suite import EvaluationSuite
from app.execution.broker import ExecutionResult
from app.planner.models import PlanStep


class ScenarioBroker:
    def __init__(self, results):
        self.results = dict(results)
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.results[request.tool_name]


class ScenarioStateManager:
    def __init__(self):
        self.calls = []

    def start_step(self, task_id, step_id):
        self.calls.append(
            ("start", task_id, step_id)
        )

    def complete_step(
        self,
        task_id,
        step_id,
        result,
        observation=None,
    ):
        self.calls.append(
            (
                "complete",
                task_id,
                step_id,
                result,
                observation,
            )
        )

    def fail_step(
        self,
        task_id,
        step_id,
        error,
        observation=None,
    ):
        self.calls.append(
            (
                "fail",
                task_id,
                step_id,
                error,
                observation,
            )
        )


def test_e2e_successful_step():
    broker = ScenarioBroker(
        {
            "SearchTool": ExecutionResult(
                tool_name="SearchTool",
                success=True,
                result={
                    "records": 3,
                    "status": "success",
                },
            )
        }
    )
    state = ScenarioStateManager()

    step = PlanStep(
        step_id="search-1",
        tool_name="SearchTool",
        description="Search records",
        inputs={"query": "active"},
    )

    result = ExecutionVerifier(
        broker,
        state,
    ).execute_and_verify(
        "task-search",
        step,
        expected_output={
            "records": 3,
            "status": "success",
        },
    )

    assert result.execution_success is True
    assert result.verification.passed is True
    assert state.calls[0][0] == "start"
    assert state.calls[1][0] == "complete"
    assert len(broker.requests) == 1


def test_e2e_wrong_business_result_fails_step():
    broker = ScenarioBroker(
        {
            "SearchTool": ExecutionResult(
                tool_name="SearchTool",
                success=True,
                result={
                    "records": 2,
                    "status": "success",
                },
            )
        }
    )
    state = ScenarioStateManager()

    step = PlanStep(
        step_id="search-2",
        tool_name="SearchTool",
        inputs={"query": "active"},
    )

    result = ExecutionVerifier(
        broker,
        state,
    ).execute_and_verify(
        "task-search-failure",
        step,
        expected_output={
            "records": 3,
            "status": "success",
        },
    )

    assert result.execution_success is True
    assert result.verification.passed is False
    assert state.calls[1][0] == "fail"
    assert not any(
        call[0] == "complete"
        for call in state.calls
    )


def test_e2e_tool_failure_propagates_to_state():
    broker = ScenarioBroker(
        {
            "DatabaseTool": ExecutionResult(
                tool_name="DatabaseTool",
                success=False,
                result={},
                error="database unavailable",
            )
        }
    )
    state = ScenarioStateManager()

    step = PlanStep(
        step_id="database-1",
        tool_name="DatabaseTool",
        inputs={"query": "SELECT 1"},
    )

    result = ExecutionVerifier(
        broker,
        state,
    ).execute_and_verify(
        "task-database",
        step,
    )

    assert result.execution_success is False
    assert result.verification.passed is False
    assert state.calls[1][0] == "fail"
    assert "database unavailable" in state.calls[1][3]


def test_e2e_multiple_independent_steps():
    broker = ScenarioBroker(
        {
            "StepA": ExecutionResult(
                tool_name="StepA",
                success=True,
                result={"value": 10},
            ),
            "StepB": ExecutionResult(
                tool_name="StepB",
                success=True,
                result={"value": 20},
            ),
        }
    )
    state = ScenarioStateManager()

    verifier = ExecutionVerifier(
        broker,
        state,
    )

    step_a = PlanStep(
        step_id="step-a",
        tool_name="StepA",
    )

    step_b = PlanStep(
        step_id="step-b",
        tool_name="StepB",
        depends_on=["step-a"],
    )

    result_a = verifier.execute_and_verify(
        "task-multi",
        step_a,
        expected_output={"value": 10},
    )

    result_b = verifier.execute_and_verify(
        "task-multi",
        step_b,
        expected_output={"value": 20},
    )

    assert result_a.verification.passed is True
    assert result_b.verification.passed is True

    completed = [
        call
        for call in state.calls
        if call[0] == "complete"
    ]

    assert len(completed) == 2
    assert len(broker.requests) == 2


def test_evaluation_suite_reports_mixed_results():
    suite = EvaluationSuite()

    cases = [
        {
            "case_id": "case-1",
            "name": "addition",
            "input_data": {"a": 2, "b": 3},
            "expected_output": 5,
        },
        {
            "case_id": "case-2",
            "name": "multiplication",
            "input_data": {"a": 4, "b": 5},
            "expected_output": 20,
        },
        {
            "case_id": "case-3",
            "name": "wrong expectation",
            "input_data": {"a": 10, "b": 2},
            "expected_output": 99,
        },
    ]

    from app.evaluation.models import EvaluationCase

    evaluation_cases = [
        EvaluationCase(**case)
        for case in cases
    ]

    summary = suite.evaluate(
        evaluation_cases,
        lambda data: data["a"] + data["b"],
    )

    assert summary.total == 3
    assert summary.passed == 1
    assert summary.failed == 2
    assert summary.success is False


def test_evaluation_suite_is_repeatable():
    suite = EvaluationSuite()

    from app.evaluation.models import EvaluationCase

    cases = [
        EvaluationCase(
            case_id="repeat-1",
            name="deterministic",
            input_data={"value": 10},
            expected_output=20,
        )
    ]

    evaluator = lambda data: data["value"] * 2

    first = suite.evaluate(cases, evaluator)
    second = suite.evaluate(cases, evaluator)

    assert first.to_dict() == second.to_dict()
