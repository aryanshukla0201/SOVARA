import json

import pytest

from app.models.ollama_adapter import OllamaAdapter


class FakeResponse:
    def __init__(self, lines):
        self.lines = lines

    def raise_for_status(self):
        pass

    def iter_lines(self, decode_unicode=True):
        return self.lines


def test_stream_generate_yields_chunks(monkeypatch):
    payload = [
        json.dumps({"response": "Hello "}).encode(),
        json.dumps({"response": "world"}).encode(),
        json.dumps({
            "response": "",
            "done": True,
            "eval_duration": 1_000_000_000,
            "eval_count": 2,
            "load_duration": 0,
            "total_duration": 2_000_000_000,
        }).encode(),
    ]

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse(payload)

    monkeypatch.setattr(
        "app.models.ollama_adapter.requests.post",
        fake_post,
    )

    adapter = OllamaAdapter("test-model")

    assert list(adapter.stream_generate("hello")) == [
        "Hello ",
        "world",
    ]

    assert captured["kwargs"]["stream"] is True
    assert captured["kwargs"]["json"]["stream"] is True


def test_stream_generate_preserves_options(monkeypatch):
    payload = [
        json.dumps({
            "response": "ok",
            "done": True,
            "eval_duration": 1_000_000_000,
            "eval_count": 1,
        }).encode(),
    ]

    captured = {}

    def fake_post(url, **kwargs):
        captured["kwargs"] = kwargs
        return FakeResponse(payload)

    monkeypatch.setattr(
        "app.models.ollama_adapter.requests.post",
        fake_post,
    )

    adapter = OllamaAdapter("test-model")

    list(
        adapter.stream_generate(
            "hello",
            num_predict=512,
            temperature=0.1,
            top_p=0.8,
            top_k=10,
            repeat_penalty=1.05,
            keep_alive="15m",
        )
    )

    options = captured["kwargs"]["json"]["options"]

    assert options["num_predict"] == 512
    assert options["temperature"] == 0.1
    assert options["top_p"] == 0.8
    assert options["top_k"] == 10
    assert options["repeat_penalty"] == 1.05
    assert captured["kwargs"]["json"]["keep_alive"] == "15m"


def test_stream_generate_reports_request_failure(monkeypatch):
    def fake_post(url, **kwargs):
        raise RuntimeError("network failure")

    monkeypatch.setattr(
        "app.models.ollama_adapter.requests.post",
        fake_post,
    )

    adapter = OllamaAdapter("test-model")

    with pytest.raises(RuntimeError):
        list(adapter.stream_generate("hello"))
