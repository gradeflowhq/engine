import pytest

from gradeflow_engine.registry import Registry


class TestRegistry:
    def test_register_and_get(self) -> None:
        r: Registry[str] = Registry("widget")
        r.register("Foo", "bar")
        assert r.get("foo") == "bar"  # case-insensitive

    def test_register_duplicate_raises(self) -> None:
        r: Registry[str] = Registry("widget")
        r.register("Foo", "bar")
        with pytest.raises(KeyError, match="already registered"):
            r.register("foo", "baz")

    def test_register_overwrite(self) -> None:
        r: Registry[str] = Registry("widget")
        r.register("x", "old")
        r.register("x", "new", overwrite=True)
        assert r.get("x") == "new"

    def test_unregister(self) -> None:
        r: Registry[str] = Registry("widget")
        r.register("x", "val")
        r.unregister("x")
        with pytest.raises(KeyError):
            r.get("x")

    def test_unregister_missing_raises(self) -> None:
        r: Registry[str] = Registry("widget")
        with pytest.raises(KeyError, match="not registered"):
            r.unregister("missing")

    def test_get_missing_lists_available(self) -> None:
        r: Registry[str] = Registry("widget")
        r.register("alpha", "a")
        r.register("beta", "b")
        with pytest.raises(KeyError, match="alpha, beta"):
            r.get("gamma")

    def test_try_get_returns_none(self) -> None:
        r: Registry[str] = Registry("widget")
        assert r.try_get("nope") is None

    def test_try_get_returns_item(self) -> None:
        r: Registry[str] = Registry("widget")
        r.register("x", "val")
        assert r.try_get("x") == "val"

    def test_available_sorted(self) -> None:
        r: Registry[str] = Registry("widget")
        r.register("Zeta", "z")
        r.register("Alpha", "a")
        assert r.available() == ["alpha", "zeta"]

    def test_normalize_strips_whitespace(self) -> None:
        r: Registry[str] = Registry("widget")
        r.register("  Foo  ", "bar")
        assert r.get("foo") == "bar"

    def test_register_decorator(self) -> None:
        r: Registry[type] = Registry("class")

        @r.register_decorator("myclass")
        class MyClass:
            pass

        assert r.get("myclass") is MyClass
