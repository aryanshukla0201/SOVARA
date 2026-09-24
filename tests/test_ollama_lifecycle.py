from unittest.mock import patch

from app.models.ollama_adapter import OllamaAdapter


def test_warm_requests_keep_alive():
    adapter = OllamaAdapter(model_name="test-model")

    with patch.object(adapter, "_call_ollama") as call:
        adapter.warm()

    call.assert_called_once_with(
        "",
        num_predict=1,
        keep_alive="30m",
    )


def test_unload_requests_zero_keep_alive():
    adapter = OllamaAdapter(model_name="test-model")

    with patch.object(adapter, "_call_ollama") as call:
        adapter.unload()

    call.assert_called_once_with(
        "",
        num_predict=1,
        keep_alive=0,
    )
