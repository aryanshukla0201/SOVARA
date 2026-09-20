from __future__ import annotations

from unittest.mock import patch

import pytest

from app.models.gateway import ModelGateway
from app.models.model_registry import ModelDescriptor
from app.models.hardware import HardwareProfile


def test_gateway_initializes():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    assert gateway is not None


def test_reasoning_resolves_to_phi4():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    adapter = gateway.resolve("reasoning")

    assert adapter.name == "phi4-mini"


def test_code_resolves_to_qwen():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    adapter = gateway.resolve("code")

    assert adapter.name == "qwen2.5-coder"


def test_vision_resolves_to_gemma():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    adapter = gateway.resolve("vision")

    assert adapter.name == "gemma3"


def test_capability_lookup():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    assert gateway.get_descriptor("phi4-mini").model_name == "phi4-mini:latest"
    assert gateway.get_descriptor(
        "qwen2.5-coder"
    ).model_name == "qwen2.5-coder:7b-instruct"


def test_unknown_task_raises():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    with pytest.raises(ValueError, match="No compatible model"):
        gateway.resolve("unknown_task")


def test_unavailable_model_is_not_selected():
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
        side_effect=lambda key: key != "qwen2.5-coder",
    ):
        with pytest.raises(ValueError, match="No compatible model"):
            gateway.resolve("code")


def test_hardware_filter_blocks_model():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Low VRAM GPU",
            vram_gb=2.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    with patch.object(gateway, "is_available", return_value=True):
        with pytest.raises(ValueError, match="No compatible model"):
            gateway.resolve("code")


def test_resolve_model_rejects_insufficient_hardware():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Low VRAM GPU",
            vram_gb=2.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    with pytest.raises(RuntimeError, match="exceeds available hardware"):
        gateway.resolve_model("qwen2.5-coder")


def test_availability_cache():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    response = {
        "models": [
            {"name": "phi4-mini:latest"},
            {"name": "qwen2.5-coder:7b-instruct"},
            {"name": "gemma3:4b-it-qat"},
        ]
    }

    with patch(
        "app.models.gateway.requests.get"
    ) as mock_get:
        mock_get.return_value.json.return_value = response
        mock_get.return_value.raise_for_status.return_value = None

        assert gateway.is_available("phi4-mini") is True
        assert gateway.is_available("qwen2.5-coder") is True
        assert gateway.is_available("gemma3") is True

        assert mock_get.call_count == 1


def test_refresh_availability_invalidates_cache():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    response = {
        "models": [
            {"name": "phi4-mini:latest"},
        ]
    }

    with patch(
        "app.models.gateway.requests.get"
    ) as mock_get:
        mock_get.return_value.json.return_value = response
        mock_get.return_value.raise_for_status.return_value = None

        gateway.is_available("phi4-mini")
        gateway.is_available("phi4-mini")

        assert mock_get.call_count == 1

        gateway.refresh_availability()

        assert mock_get.call_count == 2

def test_fallback_selects_next_compatible_model():
    class FallbackRegistry:
        def find_by_capability(self, capability):
            return [
                ModelDescriptor(
                    key="primary",
                    model_name="primary-model",
                    capabilities=frozenset({capability}),
                    priority=100,
                    minimum_vram_gb=4.0,
                ),
                ModelDescriptor(
                    key="fallback",
                    model_name="fallback-model",
                    capabilities=frozenset({capability}),
                    priority=200,
                    minimum_vram_gb=4.0,
                ),
            ]

        def get(self, key):
            raise NotImplementedError

        def list(self):
            return []

    gateway = ModelGateway(
        registry=FallbackRegistry(),
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        ),
    )

    with patch.object(
        gateway,
        "is_available",
        side_effect=lambda key: key == "fallback",
    ):
        with patch.object(
            gateway,
            "_create_adapter",
            side_effect=lambda descriptor, telemetry=None: descriptor,
        ):
            selected = gateway.resolve("reasoning")

    assert selected.key == "fallback"

def test_availability_uses_configured_ollama_endpoint_only():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    response = {
        "models": [
            {"name": "phi4-mini:latest"},
        ]
    }

    with patch(
        "app.models.gateway.requests.get"
    ) as mock_get:
        mock_get.return_value.json.return_value = response
        mock_get.return_value.raise_for_status.return_value = None

        gateway.is_available("phi4-mini")

        called_url = mock_get.call_args.args[0]

        assert called_url == (
            f"{gateway.settings.ollama_base_url}/api/tags"
        )
        assert called_url.startswith("http://localhost:11434")

def test_registry_model_name_is_propagated_to_factory():
    gateway = ModelGateway(
        hardware=HardwareProfile(
            gpu_name="Test GPU",
            vram_gb=8.0,
            ram_gb=16.0,
            platform="Windows",
        )
    )

    with patch(
        "app.models.gateway.ModelFactory.create"
    ) as mock_create:
        mock_create.return_value = object()

        descriptor = gateway.get_descriptor("qwen2.5-coder")

        gateway._create_adapter(descriptor)

        mock_create.assert_called_once_with(
            "qwen_coder",
            model_name=descriptor.model_name,
            telemetry=None,
        )
