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
def test_repair_uses_numeric_validation_expected_values_for_csv_stats(monkeypatch):
    calls = []

    class FakeModel:
        def generate(self, prompt, **kwargs):
            calls.append(prompt)

            assert (
                "Treat numeric validation `expected` values as authoritative corrections."
                in prompt
            )
            assert "137.5" in prompt
            assert "550.0" in prompt
            assert "180.0" in prompt

            return (
                "The total revenue is 550.0 units [data_1]. "
                "The average monthly revenue is 137.5 units [data_1]. "
                "The highest monthly revenue is 180.0 units on "
                "2026-04-01 [data_1]."
            )

    monkeypatch.setattr(
        "app.workflow.nodes.repair.ModelGateway.resolve",
        lambda self, role: FakeModel(),
    )

    node = RepairNode()

    result = node.repair(
        {
            "final_answer": (
                "The total revenue is 550.0 units [data_1]. "
                "The average monthly revenue cannot be calculated [data_1]. "
                "The highest recorded revenue is 180.0 units [data_1]."
            ),
            "synthesis_result": {},
        },
        [
            "numeric_validation_failed",
            (
                "numeric_validation_details: "
                "[{'evidence_id': 'data_1', "
                "'expected': {'average': 137.5, "
                "'sum': 550.0, "
                "'maximum': 180.0}}]"
            ),
        ],
        [
            {
                "evidence_id": "data_1",
                "evidence_type": "data_result",
                "result": {
                    "analysis_type": "compound",
                    "metric": "revenue",
                    "analyses": [
                        {
                            "analysis_type": "average",
                            "metric": "revenue",
                            "average": 137.5,
                            "valid_values": 4,
                        },
                        {
                            "analysis_type": "sum",
                            "metric": "revenue",
                            "sum": 550.0,
                            "valid_values": 4,
                        },
                        {
                            "analysis_type": "maximum",
                            "metric": "revenue",
                            "maximum": 180.0,
                            "record": {
                                "date": "2026-04-01",
                                "revenue": 180,
                            },
                        },
                    ],
                    "dataset_rows": 4,
                    "valid_values": 4,
                },
            }
        ],
    )

    assert len(calls) == 1
    assert result["final_answer"] == (
        "The total revenue is 550.0 units [data_1]. "
        "The average monthly revenue is 137.5 units [data_1]. "
        "The highest monthly revenue is 180.0 units on "
        "2026-04-01 [data_1]."
    )
