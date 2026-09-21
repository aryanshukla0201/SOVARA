from app.services.ttl_cache import TTLCache


def test_cache_hit_and_miss():
    cache = TTLCache[str](max_size=2, ttl_seconds=10)

    assert cache.get("missing") is None

    cache.set("key", "value")

    assert cache.get("key") == "value"


def test_cache_expires():
    now = [100.0]
    cache = TTLCache[str](
        max_size=2,
        ttl_seconds=5,
        clock=lambda: now[0],
    )

    cache.set("key", "value")
    assert cache.get("key") == "value"

    now[0] = 105.0

    assert cache.get("key") is None


def test_cache_evicts_least_recently_used():
    cache = TTLCache[str](max_size=2, ttl_seconds=10)

    cache.set("a", "A")
    cache.set("b", "B")

    assert cache.get("a") == "A"

    cache.set("c", "C")

    assert cache.get("a") == "A"
    assert cache.get("b") is None
    assert cache.get("c") == "C"


def test_cache_invalidate_and_clear():
    cache = TTLCache[str](max_size=2, ttl_seconds=10)

    cache.set("a", "A")
    cache.set("b", "B")

    cache.invalidate("a")

    assert cache.get("a") is None
    assert cache.get("b") == "B"

    cache.clear()

    assert len(cache) == 0
