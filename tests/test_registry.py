import pytest

from gradeflow_engine.adapters.registries import AdapterRegistry
from gradeflow_engine.exceptions import AdapterNotFoundError, SerializerNotFoundError
from gradeflow_engine.registry import Registry
from gradeflow_engine.serializations.registries import SerializerRegistry


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


class TestAdapterRegistry:
    def test_get_missing_raises_adapter_not_found_error(self) -> None:
        r: AdapterRegistry = AdapterRegistry("csv_adapter")
        with pytest.raises(AdapterNotFoundError) as exc_info:
            r.get("nonexistent")
        assert exc_info.value.name == "nonexistent"
        assert exc_info.value.kind == "csv_adapter"

    def test_adapter_not_found_error_lists_available(self) -> None:
        r: AdapterRegistry = AdapterRegistry("my_adapter")
        r.register("alpha", object)
        r.register("beta", object)
        with pytest.raises(AdapterNotFoundError) as exc_info:
            r.get("gamma")
        assert "alpha" in exc_info.value.available
        assert "beta" in exc_info.value.available

    def test_adapter_not_found_is_subclass_of_gradeflow_error(self) -> None:
        from gradeflow_engine.exceptions import AdapterError, GradeFlowError

        r: AdapterRegistry = AdapterRegistry("some_adapter")
        with pytest.raises(GradeFlowError):
            r.get("missing")
        with pytest.raises(AdapterError):
            r.get("missing")


class TestSerializerRegistry:
    def test_get_missing_raises_serializer_not_found_error(self) -> None:
        r: SerializerRegistry = SerializerRegistry("rubric_serializer")
        with pytest.raises(SerializerNotFoundError) as exc_info:
            r.get("nonexistent")
        assert exc_info.value.name == "nonexistent"

    def test_serializer_not_found_error_lists_available(self) -> None:
        r: SerializerRegistry = SerializerRegistry("question_set_serializer")
        r.register("yaml", object)  # type: ignore[arg-type]
        with pytest.raises(SerializerNotFoundError) as exc_info:
            r.get("json")
        assert "yaml" in exc_info.value.available

    def test_serializer_not_found_is_subclass_of_gradeflow_error(self) -> None:
        from gradeflow_engine.exceptions import GradeFlowError, SerializationError

        r: SerializerRegistry = SerializerRegistry("submissions_serializer")
        with pytest.raises(GradeFlowError):
            r.get("missing")
        with pytest.raises(SerializationError):
            r.get("missing")
