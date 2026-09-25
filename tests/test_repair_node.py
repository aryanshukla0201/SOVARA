from app.workflow.nodes.repair import RepairNode


def test_repair_runs_when_numeric_validation_failed(monkeypatch):
    calls = []

    class FakeModel:
        def generate(self, prompt, **kwargs):
            calls.append(prompt)
            return "Revenue increased from 100 to 180, representing an 80% increase [data_1]"

    monkeypatch.setattr(
        "app.workflow.nodes.repair.ModelGateway.resolve",
        lambda self, role: FakeModel(),
    )

    node = RepairNode()

    result = node.repair(
        {
            "final_answer": (
                "Revenue increased from 100 to 190, "
                "representing a 90% increase [data_1]"
            ),
            "synthesis_result": {},
        },
        [
            "numeric_validation_failed",
            (
                "numeric_validation_details: "
                "[{'evidence_id': 'data_1', "
                "'expected': {'start_value': 100.0, "
                "'end_value': 180.0, "
                "'percentage_change': 80.0}}]"
            ),
        ],
        [
            {
                "evidence_id": "data_1",
                "evidence_type": "data_result",
                "result": {
                    "analysis_type": "trend_analysis",
                    "metric": "revenue",
                    "start_value": 100.0,
                    "end_value": 180.0,
                    "percentage_change": 80.0,
                },
            }
        ],
    )

    assert len(calls) == 1
    assert result["final_answer"] == (
        "Revenue increased from 100 to 180, "
        "representing an 80% increase [data_1]"
    )
