from unittest.mock import Mock

import pytest

from app.models.fallback_adapter import FallbackModelAdapter


def test_fallback_uses_primary_when_successful():
    primary = Mock()
    primary.name = "primary"
    primary.generate.return_value = "primary result"

    fallback = Mock()
    fallback.name = "fallback"

    adapter = FallbackModelAdapter(
        primary=primary,
        fallbacks=[fallback],
    )

    result = adapter.generate("hello")

    assert result == "primary result"
    primary.generate.assert_called_once()
    fallback.generate.assert_not_called()


def test_fallback_uses_next_model_after_runtime_failure():
    primary = Mock()
    primary.name = "primary"
    primary.generate.side_effect = RuntimeError("model unavailable")

    fallback = Mock()
    fallback.name = "fallback"
    fallback.generate.return_value = "fallback result"

    adapter = FallbackModelAdapter(
        primary=primary,
        fallbacks=[fallback],
    )

    result = adapter.generate("hello")

    assert result == "fallback result"
    primary.generate.assert_called_once()
    fallback.generate.assert_called_once()


def test_fallback_reports_transition():
    primary = Mock()
    primary.name = "primary"
    primary.generate.side_effect = RuntimeError("connection failed")

    fallback = Mock()
    fallback.name = "fallback"
    fallback.generate.return_value = "ok"

    transitions = []

    adapter = FallbackModelAdapter(
        primary=primary,
        fallbacks=[fallback],
        on_fallback=lambda source, target, error: transitions.append(
            (source, target, error)
        ),
    )

    assert adapter.generate("hello") == "ok"
    assert transitions == [
        ("primary", "fallback", "connection failed")
    ]


def test_fallback_raises_when_all_models_fail():
    primary = Mock()
    primary.name = "primary"
    primary.generate.side_effect = RuntimeError("primary failed")

    fallback = Mock()
    fallback.name = "fallback"
    fallback.generate.side_effect = RuntimeError("fallback failed")

    adapter = FallbackModelAdapter(
        primary=primary,
        fallbacks=[fallback],
    )

    with pytest.raises(RuntimeError, match="fallback failed"):
        adapter.generate("hello")


def test_fallback_supports_structured_generation():
    primary = Mock()
    primary.name = "primary"
    primary.generate_structured.side_effect = RuntimeError("failed")

    fallback = Mock()
    fallback.name = "fallback"
    fallback.generate_structured.return_value = {"answer": "ok"}

    adapter = FallbackModelAdapter(
        primary=primary,
        fallbacks=[fallback],
    )

    result = adapter.generate_structured(
        "hello",
        {"type": "object"},
    )

    assert result == {"answer": "ok"}
