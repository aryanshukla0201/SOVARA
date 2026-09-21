from pathlib import Path
from unittest.mock import patch

from app.models.gemma_adapter import GemmaAdapter
from app.models.hardware import HardwareProfile
from app.models.gateway import ModelGateway
from app.tools.vision.image_analyzer import VisionAnalyzer


def test_gemma_adapter_sends_image_to_ollama(tmp_path):
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"fake-image-data")

    response = {
        "response": '{"observations":[{"description":"A test image","confidence":0.9}]}'
    }

    with patch(
        "app.models.gemma_adapter.requests.post"
    ) as mock_post:

        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = response

        adapter = GemmaAdapter(
            model_name="gemma3:4b-it-qat",
            base_url="http://localhost:11434",
        )

        result = adapter.analyze_image(
            str(image_path),
            "Analyze this test image.",
        )

        assert result["image_id"] == "test.png"
        assert result["model"] == "gemma3:4b-it-qat"
        assert result["observations"][0]["description"] == "A test image"

        payload = mock_post.call_args.kwargs["json"]

        assert payload["model"] == "gemma3:4b-it-qat"
        assert payload["stream"] is False
        assert len(payload["images"]) == 1
        assert payload["images"][0] != ""


def test_gemma_adapter_rejects_missing_image(tmp_path):
    adapter = GemmaAdapter(
        model_name="gemma3:4b-it-qat",
        base_url="http://localhost:11434",
    )

    missing = tmp_path / "missing.png"

    try:
        adapter.analyze_image(
            str(missing),
            "Analyze image.",
        )
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_vision_analyzer_uses_model_gateway(tmp_path):
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"fake-image")

    class FakeAdapter:
        name = "gemma3"

        def analyze_image(self, image_path, task_context):
            return {
                "image_id": Path(image_path).name,
                "model": "gemma3",
                "observations": [
                    {
                        "description": task_context,
                        "confidence": 1.0,
                    }
                ],
            }

    class FakeGateway:
        def resolve(self, task_type, telemetry=None):
            assert task_type == "vision"
            return FakeAdapter()

    analyzer = VisionAnalyzer(
        gateway=FakeGateway(),
    )

    result = analyzer.analyze(
        str(image_path),
        "test multimodal task",
    )

    assert result["model"] == "gemma3"
    assert result["observations"][0]["description"] == (
        "test multimodal task"
    )


def test_gateway_vision_still_resolves_to_gemma():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    with patch.object(
        gateway,
        "is_available",
        return_value=True,
    ):
        adapter = gateway.resolve("vision")

    assert adapter.name == "gemma3"
