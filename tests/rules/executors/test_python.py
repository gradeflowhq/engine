import pytest

from gradeflow_engine.exceptions import ExecutorRuntimeError, ExecutorTimeoutError
from gradeflow_engine.rules.executors.python import (
    _decode_variables,
    _encode_variables,
    _from_json_safe,
    _is_json_safe,
    _to_json_safe,
    run,
)


class TestJsonSafe:
    def test_set_round_trip(self) -> None:
        encoded = _to_json_safe({1, 2, 3})
        assert encoded["__type__"] == "set"
        decoded = _from_json_safe(encoded)
        assert decoded == {1, 2, 3}

    def test_non_set_passthrough(self) -> None:
        assert _to_json_safe("hello") == "hello"
        assert _to_json_safe(42) == 42
        assert _from_json_safe("hello") == "hello"

    def test_dict_without_tag_unchanged(self) -> None:
        d = {"key": "val"}
        assert _from_json_safe(d) == d

    def test_is_json_safe_rejects_non_json_values(self) -> None:
        assert _is_json_safe({"x": [1]}) is True
        assert _is_json_safe(object()) is False


class TestEncodeDecodeVariables:
    def test_encode_decode_round_trip(self) -> None:
        variables = {"x": 1, "name": "hello", "items": {10, 20}}
        encoded = _encode_variables(variables)
        decoded = _decode_variables(encoded)
        assert decoded["x"] == 1
        assert decoded["name"] == "hello"
        assert decoded["items"] == {10, 20}

    def test_encode_non_serializable_raises(self) -> None:
        with pytest.raises(TypeError, match="JSON-serializable"):
            _encode_variables({"obj": object()})

    def test_decode_malformed_json_raises(self) -> None:
        with pytest.raises(ExecutorRuntimeError, match="Failed to parse"):
            _decode_variables("{bad json")


class TestRun:
    def test_basic_execution(self) -> None:
        variables: dict = {"x": 5}
        run("x = x * 2", variables, time_limit_s=5)
        assert variables["x"] == 10

    def test_set_round_trip(self) -> None:
        variables: dict = {"s": {1, 2, 3}}
        run("s = s | {4}", variables, time_limit_s=5)
        assert variables["s"] == {1, 2, 3, 4}

    def test_runtime_error_raises(self) -> None:
        with pytest.raises(ExecutorRuntimeError):
            run("1 / 0", {"x": 1}, time_limit_s=5)

    def test_timeout_raises(self) -> None:
        with pytest.raises(ExecutorTimeoutError, match="timed out"):
            run("while True: pass", {}, time_limit_s=1)
