from app.workflow.nodes.reasoning_node import ReasoningNode


def _build_node(monkeypatch, response, captured):
    class FakeModel:
        name = "fake-reasoning-model"

        def generate(self, prompt, **kwargs):
            captured["prompt"] = prompt
            return response

    monkeypatch.setattr(
        "app.workflow.nodes.reasoning_node.ModelGateway.resolve",
        lambda self, role: FakeModel(),
    )

    return ReasoningNode()


def test_conversational_memory_wins_for_name_recall(monkeypatch):
    captured = {}

    node = _build_node(
        monkeypatch,
        "You told me that your name is Aryan.",
        captured,
    )

    result = node.run(
        user_query="What name did I tell you?",
        evidence=[
            {
                "evidence_id": "vault_001",
                "evidence_type": "document",
                "content": "The user's name is Bob.",
            }
        ],
        conversation_history=[
            {
                "role": "user",
                "content": "My name is Aryan.",
            }
        ],
    )

    assert "CONVERSATION HISTORY:" in captured["prompt"]
    assert "My name is Aryan." in captured["prompt"]
    assert "The user's name is Bob." in captured["prompt"]
    assert "conversation_history is" in captured["prompt"]
    assert "authoritative." in captured["prompt"]
    assert "Do NOT substitute Knowledge Vault" in captured["prompt"]

    assert result["answer"] == "You told me that your name is Aryan."
    assert "Bob" not in result["answer"]


def test_previous_message_recall_uses_conversation_history(monkeypatch):
    captured = {}

    node = _build_node(
        monkeypatch,
        'You said: "What is the capital of France?"',
        captured,
    )

    result = node.run(
        user_query="What did I say immediately before this?",
        evidence=[
            {
                "evidence_id": "vault_002",
                "evidence_type": "document",
                "content": "The previous user message was 'Tell me a joke.'",
            }
        ],
        conversation_history=[
            {
                "role": "user",
                "content": "What is the capital of France?",
            },
            {
                "role": "assistant",
                "content": "Paris.",
            },
        ],
    )

    assert "What is the capital of France?" in captured["prompt"]
    assert "previous-message recall" in captured["prompt"]
    assert "conversational recall" in captured["prompt"]

    assert result["answer"] == 'You said: "What is the capital of France?"'
    assert "Tell me a joke" not in result["answer"]


def test_document_query_still_uses_authoritative_evidence_citation(
    monkeypatch,
):
    captured = {}

    node = _build_node(
        monkeypatch,
        (
            "The document states that the power stroke ignites the "
            "compressed air-fuel mixture [doc_001]."
        ),
        captured,
    )

    result = node.run(
        user_query="What does the document say about the power stroke?",
        evidence=[
            {
                "evidence_id": "doc_001",
                "evidence_type": "document",
                "content": (
                    "During the power stroke, the spark plug ignites "
                    "the compressed air-fuel mixture."
                ),
            }
        ],
        conversation_history=[
            {
                "role": "user",
                "content": "My name is Aryan.",
            }
        ],
    )

    assert "[doc_001]" in captured["prompt"]
    assert "the exact evidence ID supplied in AUTHORITATIVE EVIDENCE" in (
        captured["prompt"]
    )

    assert "[doc_001]" in result["answer"]
    assert "doc_001" in result["reasoning"]


def test_mixed_conversation_and_evidence_query_uses_each_source_for_its_part(
    monkeypatch,
):
    captured = {}

    node = _build_node(
        monkeypatch,
        (
            "You told me that your project is called Atlas. "
            "The document identifies the project as SOVARA [doc_002]."
        ),
        captured,
    )

    result = node.run(
        user_query=(
            "What project name did I tell you, and what project name "
            "does the document identify?"
        ),
        evidence=[
            {
                "evidence_id": "doc_002",
                "evidence_type": "document",
                "content": "Project name: SOVARA",
            }
        ],
        conversation_history=[
            {
                "role": "user",
                "content": "My project is called Atlas.",
            }
        ],
    )

    assert "My project is called Atlas." in captured["prompt"]
    assert "Project name: SOVARA" in captured["prompt"]
    assert "3. MIXED REQUESTS" in captured["prompt"]
    assert "conversational recall -> conversation_history" in captured["prompt"]
    assert (
        "file/document/data/code/vision claims -> authoritative evidence"
        in captured["prompt"]
    )

    assert "Atlas" in result["answer"]
    assert "SOVARA" in result["answer"]
    assert "[doc_002]" in result["answer"]