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
