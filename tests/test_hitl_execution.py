from dataclasses import dataclass

from app.execution.broker import ExecutionRequest, ExecutionResult
from app.governance.models import Policy, RiskLevel
from app.governance.observability import Observability
from app.governance.policy import PolicyEngine
from app.hitl.execution import ApprovalExecutionGate
from app.hitl.manager import ApprovalManager


@dataclass
class FakeSpec:
    tool_name: str = "ToolA"
    capability: str = "test"
    input_schema: dict = None
    output_schema: dict = None
    allowed_task_types: list = None
    description: str = ""
    risk_level: str = "high"
    permissions: list = None
    execution_method: str = "local"
    timeout_seconds: int = 30
    enabled: bool = True

    def __post_init__(self):
        if self.input_schema is None:
            self.input_schema = {}
        if self.output_schema is None:
            self.output_schema = {}
        if self.allowed_task_types is None:
            self.allowed_task_types = []
        if self.permissions is None:
            self.permissions = []


class FakeRegistry:
    def __init__(self):
        self.spec = FakeSpec()

    def get(self, name):
        if name != self.spec.tool_name:
            raise KeyError(name)
        return self.spec


class RecordingBroker:
    def __init__(self):
        self.registry = FakeRegistry()

        # Allow P7 to pass high-risk tools so P9 can apply
        # the human approval gate.
        self.governance_policy = Policy(
            max_risk_level=RiskLevel.CRITICAL,
        )

        self.policy_engine = PolicyEngine()
        self.observability = Observability()
        self.calls = []

    def execute(self, request):
        self.calls.append(request)

        return ExecutionResult(
            tool_name=request.tool_name,
            success=True,
            result={"ok": True},
        )


def create_manager(tmp_path):
    return ApprovalManager(
        database_path=tmp_path / "approvals.db"
    )


def test_high_risk_is_blocked_until_approval(tmp_path):
    broker = RecordingBroker()
    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    result = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            arguments={"value": 10},
            task_id="task-1",
        ),
        step_id="step-1",
    )

    assert result.status == "pending"
    assert result.approval_required is True
    assert result.approval_id is not None
    assert broker.calls == []


def test_approved_request_reaches_broker(tmp_path):
    broker = RecordingBroker()
    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    submitted = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            arguments={"value": 10},
            task_id="task-1",
        ),
        step_id="step-1",
    )

    result = gate.approve_and_execute(
        submitted.approval_id,
    )

    assert result.status == "executed"
    assert result.execution_result is not None
    assert len(broker.calls) == 1
    assert broker.calls[0].tool_name == "ToolA"


def test_rejected_request_does_not_reach_broker(tmp_path):
    broker = RecordingBroker()
    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    submitted = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            task_id="task-1",
        ),
        step_id="step-1",
    )

    result = gate.reject(
        submitted.approval_id,
        reason="human rejected",
    )

    assert result.status == "rejected"
    assert broker.calls == []


def test_low_risk_request_executes_without_approval(tmp_path):
    broker = RecordingBroker()
    broker.registry.spec.risk_level = "low"

    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    result = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            task_id="task-1",
        ),
        step_id="step-1",
    )

    assert result.status == "executed"
    assert result.approval_required is False
    assert result.approval_id is None
    assert len(broker.calls) == 1


def test_approval_events_are_audited(tmp_path):
    broker = RecordingBroker()
    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    submitted = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            task_id="task-1",
        ),
        step_id="step-1",
    )

    gate.approve_and_execute(submitted.approval_id)

    events = broker.observability.get_events("task-1")
    event_types = [event.event_type for event in events]

    assert "approval_requested" in event_types
    assert "approval_approved" in event_types

def test_expired_approval_cannot_execute(tmp_path):
    broker = RecordingBroker()
    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    submitted = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            task_id="task-1",
        ),
        step_id="step-1",
    )

    gate.expire(submitted.approval_id)

    try:
        gate.approve_and_execute(submitted.approval_id)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "expired approval must not execute"
        )

    assert broker.calls == []


def test_rejection_is_audited(tmp_path):
    broker = RecordingBroker()
    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    submitted = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            task_id="task-1",
        ),
        step_id="step-1",
    )

    gate.reject(
        submitted.approval_id,
        reason="human rejected",
    )

    events = broker.observability.get_events("task-1")
    event_types = [event.event_type for event in events]

    assert "approval_requested" in event_types
    assert "approval_rejected" in event_types


def test_expiration_is_audited(tmp_path):
    broker = RecordingBroker()
    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    submitted = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            task_id="task-1",
        ),
        step_id="step-1",
    )

    gate.expire(submitted.approval_id)

    events = broker.observability.get_events("task-1")
    event_types = [event.event_type for event in events]

    assert "approval_requested" in event_types
    assert "approval_expired" in event_types


def test_cancellation_is_audited(tmp_path):
    broker = RecordingBroker()
    manager = create_manager(tmp_path)
    gate = ApprovalExecutionGate(
        broker=broker,
        approval_manager=manager,
    )

    submitted = gate.submit(
        ExecutionRequest(
            tool_name="ToolA",
            task_id="task-1",
        ),
        step_id="step-1",
    )

    gate.cancel(submitted.approval_id)

    events = broker.observability.get_events("task-1")
    event_types = [event.event_type for event in events]

    assert "approval_requested" in event_types
    assert "approval_cancelled" in event_types


