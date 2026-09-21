from app.execution.broker import ExecutionBroker, ExecutionRequest
from app.execution.handlers import ToolExecutionHandlers
from app.governance.audit import AuditEventType
from app.governance.models import Policy, RiskLevel
from app.governance.observability import Observability
from app.tools.registry import ToolRegistry, ToolSpec


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            tool_name="TestTool",
            capability="test",
            input_schema={},
            output_schema={"result": "object"},
            risk_level="low",
            permissions=["local_files"],
            execution_method="local",
            timeout_seconds=10,
        )
    )
    return registry


def make_handlers(calls: list[dict]) -> ToolExecutionHandlers:
    handlers = ToolExecutionHandlers()

    def handler(**arguments):
        calls.append(arguments)
        return {"ok": True}

    handlers.register("TestTool", handler)
    return handlers


def test_governance_allows_execution_and_records_events():
    calls = []
    observability = Observability()

    broker = ExecutionBroker(
        registry=make_registry(),
        handlers=make_handlers(calls),
        governance_policy=Policy(
            allowed_tools=frozenset({"TestTool"}),
            allowed_permissions=frozenset({"local_files"}),
            allowed_execution_methods=frozenset({"local"}),
        ),
        observability=observability,
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="TestTool",
            arguments={"value": 1},
            task_id="task-1",
        )
    )

    assert result.success
    assert calls == [{"value": 1}]

    events = observability.get_events("task-1")
    assert [event.event_type for event in events] == [
        AuditEventType.POLICY_ALLOWED,
        AuditEventType.EXECUTION_STARTED,
        AuditEventType.EXECUTION_COMPLETED,
    ]


def test_governance_denial_prevents_handler_execution():
    calls = []
    observability = Observability()

    broker = ExecutionBroker(
        registry=make_registry(),
        handlers=make_handlers(calls),
        governance_policy=Policy(
            allowed_tools=frozenset({"OtherTool"}),
        ),
        observability=observability,
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="TestTool",
            task_id="task-2",
        )
    )

    assert not result.success
    assert "not permitted by policy" in result.error
    assert calls == []

    events = observability.get_events("task-2")
    assert len(events) == 1
    assert events[0].event_type == AuditEventType.POLICY_DENIED
    assert events[0].decision == "deny"
    assert "not permitted by policy" in events[0].reason


def test_governance_denial_for_execution_method_prevents_handler():
    calls = []
    observability = Observability()

    broker = ExecutionBroker(
        registry=make_registry(),
        handlers=make_handlers(calls),
        governance_policy=Policy(
            allowed_execution_methods=frozenset({"sandbox"}),
        ),
        observability=observability,
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="TestTool",
            task_id="task-3",
        )
    )

    assert not result.success
    assert "execution method local is not permitted" in result.error
    assert calls == []


def test_unknown_tool_is_audited_as_policy_denial():
    observability = Observability()

    broker = ExecutionBroker(
        registry=make_registry(),
        observability=observability,
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="UnknownTool",
            task_id="task-4",
        )
    )

    assert not result.success

    events = observability.get_events("task-4")
    assert len(events) == 1
    assert events[0].event_type == AuditEventType.POLICY_DENIED
    assert "Unknown tool" in events[0].reason


def test_p5_policy_still_blocks_after_governance_allows():
    calls = []
    observability = Observability()

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            tool_name="HighRiskTool",
            capability="test",
            input_schema={},
            output_schema={},
            risk_level="high",
            permissions=[],
            execution_method="local",
            timeout_seconds=10,
        )
    )

    broker = ExecutionBroker(
        registry=registry,
        handlers=make_handlers(calls),
        governance_policy=Policy(
            allowed_tools=frozenset({"HighRiskTool"}),
            max_risk_level=RiskLevel.HIGH,
            allowed_execution_methods=frozenset({"local"}),
        ),
        observability=observability,
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="HighRiskTool",
            task_id="task-5",
        )
    )

    assert not result.success
    assert "Risk level is not allowed: high" in result.error
    assert calls == []
