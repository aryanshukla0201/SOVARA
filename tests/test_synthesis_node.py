from app.workflow.nodes.synthesis import SynthesisNode


def test_synthesis_preserves_document_evidence_ids(monkeypatch):
    captured = {}

    class FakeModel:
        def generate(self, prompt, **kwargs):
            captured["prompt"] = prompt
            return "The document states the power stroke ignites the compressed air-fuel mixture [file_0e1deb0e_ev_001]"

    monkeypatch.setattr(
        "app.workflow.nodes.synthesis.ModelGateway.resolve",
        lambda self, role: FakeModel(),
    )

    node = SynthesisNode()

    result = node.run(
        user_query="What does the document say about the power stroke?",
        evidence=[
            {
                "evidence_id": "file_0e1deb0e_ev_001",
                "evidence_type": "document",
                "content": (
                    "During the power stroke, the spark plug ignites "
                    "the compressed air-fuel mixture."
                ),
                "relevance_score": 0.7633,
            }
        ],
        data_results=[],
        code_results=[],
        vision_results=[],
    )

    assert "[file_0e1deb0e_ev_001]" in captured["prompt"]
    assert "file_0e1deb0e_ev_001" in result["evidence_references"]

def test_synthesis_reads_nested_evidence_fields(monkeypatch):
    captured = {}

    class FakeModel:
        def generate(self, prompt, **kwargs):
            captured["prompt"] = prompt
            return (
                "The highest monthly revenue was 180.0 on "
                "2026-04-01 [data_1]."
            )

    monkeypatch.setattr(
        "app.workflow.nodes.synthesis.ModelGateway.resolve",
        lambda self, role: FakeModel(),
    )

    node = SynthesisNode()

    result = node.run(
        user_query="What date had the highest revenue?",
        evidence=[],
        data_results=[
            {
                "evidence_id": "data_1",
                "evidence_type": "data_result",
                "result": {
                    "analysis_type": "compound",
                    "analyses": [
                        {
                            "analysis_type": "maximum",
                            "metric": "revenue",
                            "maximum": 180.0,
                            "record": {
                                "date": "2026-04-01",
                                "revenue": 180,
                            },
                        }
                    ],
                },
                "relevance_score": 0.9,
            }
        ],
        code_results=[],
        vision_results=[],
    )

    assert (
        "Inspect the full structure of each authoritative evidence item"
        in captured["prompt"]
    )
    assert "nested objects such as records, analyses, metadata" in captured["prompt"]
    assert "Do not state that a value, date, field, or fact is missing" in captured[
        "prompt"
    ]
    assert "2026-04-01" in captured["prompt"]
    assert "data_1" in result["evidence_references"]
