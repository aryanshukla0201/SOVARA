from types import SimpleNamespace

from app.evaluation.integration import ExecutionVerifier
from app.planner.models import PlanStep
from app.execution.broker import ExecutionResult


class FakeBroker:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.result


class FakeStateManager:
    def __init__(self):
        self.calls = []

    def start_step(self, task_id, step_id):
        self.calls.append(("start", task_id, step_id))

    def complete_step(self, task_id, step_id, result, observation=None):
        self.calls.append(
            ("complete", task_id, step_id, result, observation)
        )

    def fail_step(self, task_id, step_id, error, observation=None):
        self.calls.append(
            ("fail", task_id, step_id, error, observation)
        )


def test_execution_success_is_verified_and_completed():
    broker = FakeBroker(
        ExecutionResult(
            tool_name="EchoTool",
            success=True,
            result={"value": "ok"},
        )
    )
    state = FakeStateManager()

    step = PlanStep(
        step_id="step-1",
        tool_name="EchoTool",
        inputs={"value": "ok"},
    )

    result = ExecutionVerifier(broker, state).execute_and_verify(
        "task-1",
        step,
        expected_output={"value": "ok"},
    )

    assert result.execution_success is True
    assert result.verification.passed is True
    assert state.calls[0] == ("start", "task-1", "step-1")
    assert state.calls[1][0] == "complete"
    assert broker.requests[0].tool_name == "EchoTool"
    assert broker.requests[0].arguments == {"value": "ok"}
    assert broker.requests[0].task_id == "task-1"


def test_output_mismatch_fails_step():
    broker = FakeBroker(
        ExecutionResult(
            tool_name="EchoTool",
            success=True,
            result={"value": "actual"},
        )
    )
    state = FakeStateManager()

    step = PlanStep(
        step_id="step-1",
        tool_name="EchoTool",
    )

    result = ExecutionVerifier(broker, state).execute_and_verify(
        "task-1",
        step,
        expected_output={"value": "expected"},
    )

    assert result.execution_success is True
    assert result.verification.passed is False
    assert state.calls[1][0] == "fail"


def test_execution_failure_fails_step():
    broker = FakeBroker(
        ExecutionResult(
            tool_name="EchoTool",
            success=False,
            result={},
            error="tool failed",
        )
    )
    state = FakeStateManager()

    step = PlanStep(
        step_id="step-1",
        tool_name="EchoTool",
    )

    result = ExecutionVerifier(broker, state).execute_and_verify(
        "task-1",
        step,
    )

    assert result.execution_success is False
    assert result.verification.passed is False
    assert state.calls[1][0] == "fail"
    assert state.calls[1][3] == "tool failed"


def test_success_without_expected_output_verifies_execution():
    broker = FakeBroker(
        ExecutionResult(
            tool_name="EchoTool",
            success=True,
            result={"value": "ok"},
        )
    )
    state = FakeStateManager()

    step = PlanStep(
        step_id="step-1",
        tool_name="EchoTool",
    )

    result = ExecutionVerifier(broker, state).execute_and_verify(
        "task-1",
        step,
    )

    assert result.verification.passed is True
    assert state.calls[1][0] == "complete"
from app.evaluation.integration import ExecutionVerifier
from app.evaluation.models import VerificationStatus
from app.evaluation.verifier import DeterministicVerifier
from app.execution.broker import ExecutionResult
from app.planner.models import PlanStep


class FakeBroker:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.result


class FakeStateManager:
    def __init__(self):
        self.calls = []

    def start_step(self, task_id, step_id):
        self.calls.append(("start", task_id, step_id))

    def complete_step(self, task_id, step_id, result, observation=None):
        self.calls.append(
            ("complete", task_id, step_id, result, observation)
        )

    def fail_step(self, task_id, step_id, error, observation=None):
        self.calls.append(
            ("fail", task_id, step_id, error, observation)
        )


def test_required_fields_pass_when_all_fields_exist():
    verifier = DeterministicVerifier()

    result = verifier.verify_required_fields(
        {"id": 10, "name": "Abhay"},
        ["id", "name"],
    )

    assert result.status == VerificationStatus.PASSED
    assert result.passed is True


def test_required_fields_fail_when_field_is_missing():
    verifier = DeterministicVerifier()

    result = verifier.verify_required_fields(
        {"id": 10},
        ["id", "name"],
    )

    assert result.status == VerificationStatus.FAILED
    assert result.passed is False
    assert "name" in result.details["missing_fields"]


def test_verification_is_deterministic_for_same_inputs():
    verifier = DeterministicVerifier()

    first = verifier.verify_output(
        {"status": "completed"},
        {"status": "completed"},
        check="determinism",
    )
    second = verifier.verify_output(
        {"status": "completed"},
        {"status": "completed"},
        check="determinism",
    )

    assert first.to_dict() == second.to_dict()


def test_failed_verification_does_not_complete_step():
    broker = FakeBroker(
        ExecutionResult(
            tool_name="EchoTool",
            success=True,
            result={"value": "wrong"},
        )
    )
    state = FakeStateManager()

    step = PlanStep(
        step_id="step-verify-fail",
        tool_name="EchoTool",
    )

    result = ExecutionVerifier(broker, state).execute_and_verify(
        "task-verify",
        step,
        expected_output={"value": "correct"},
    )

    assert result.verification.passed is False
    assert state.calls[0] == (
        "start",
        "task-verify",
        "step-verify-fail",
    )
    assert state.calls[1][0] == "fail"
    assert not any(call[0] == "complete" for call in state.calls)


def test_execution_failure_does_not_complete_step():
    broker = FakeBroker(
        ExecutionResult(
            tool_name="EchoTool",
            success=False,
            result={},
            error="execution error",
        )
    )
    state = FakeStateManager()

    step = PlanStep(
        step_id="step-execution-fail",
        tool_name="EchoTool",
    )

    result = ExecutionVerifier(broker, state).execute_and_verify(
        "task-fail",
        step,
    )

    assert result.execution_success is False
    assert result.verification.passed is False
    assert state.calls[1][0] == "fail"
    assert not any(call[0] == "complete" for call in state.calls)


def test_success_without_expected_output_only_verifies_execution():
    broker = FakeBroker(
        ExecutionResult(
            tool_name="EchoTool",
            success=True,
            result={"unexpected": "data"},
        )
    )
    state = FakeStateManager()

    step = PlanStep(
        step_id="step-no-expected",
        tool_name="EchoTool",
    )

    result = ExecutionVerifier(broker, state).execute_and_verify(
        "task-no-expected",
        step,
    )

    assert result.execution_success is True
    assert result.verification.passed is True
    assert state.calls[1][0] == "complete"


def test_plan_step_inputs_are_copied_into_execution_request():
    broker = FakeBroker(
        ExecutionResult(
            tool_name="EchoTool",
            success=True,
            result={"ok": True},
        )
    )
    state = FakeStateManager()

    inputs = {"name": "test", "count": 2}

    step = PlanStep(
        step_id="step-inputs",
        tool_name="EchoTool",
        inputs=inputs,
    )

    ExecutionVerifier(broker, state).execute_and_verify(
        "task-inputs",
        step,
    )

    assert broker.requests[0].arguments == inputs
    assert broker.requests[0].arguments is not inputs
