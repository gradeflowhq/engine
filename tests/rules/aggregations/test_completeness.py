import pytest

from gradeflow_engine.rules.aggregations.completeness import output_fn, passed_fn, points_fn
from gradeflow_engine.rules.result import Result


class TestOutputFn:
    def test_all_mode_all_pass(self) -> None:
        assert output_fn([True, True, True], "ALL") == 1.0

    def test_all_mode_one_fail(self) -> None:
        assert output_fn([True, False, True], "ALL") == 0.0

    def test_any_mode_one_pass(self) -> None:
        assert output_fn([False, True, False], "ANY") == 1.0

    def test_any_mode_none_pass(self) -> None:
        assert output_fn([False, False], "ANY") == 0.0

    def test_partial_mode_fraction(self) -> None:
        assert output_fn([True, False, True, False], "PARTIAL") == 0.5

    def test_partial_mode_all_pass(self) -> None:
        assert output_fn([True, True], "PARTIAL") == 1.0

    def test_partial_mode_none_pass(self) -> None:
        assert output_fn([False, False, False], "PARTIAL") == 0.0

    def test_unsupported_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported aggregation mode"):
            output_fn([True], "UNKNOWN")  # type: ignore[arg-type]


class TestPassedFn:
    def test_all_mode(self) -> None:
        assert passed_fn([True, True], "ALL") is True
        assert passed_fn([True, False], "ALL") is False

    def test_any_mode(self) -> None:
        assert passed_fn([False, True], "ANY") is True
        assert passed_fn([False, False], "ANY") is False

    def test_partial_mode_uses_any(self) -> None:
        assert passed_fn([True, False], "PARTIAL") is True
        assert passed_fn([False, False], "PARTIAL") is False

    def test_unsupported_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported aggregation mode"):
            passed_fn([True], "WRONG")  # type: ignore[arg-type]


class TestPointsFn:
    def _make_result(self, output: float, passed: bool) -> Result:
        return Result(output=output, passed=passed, feedback="", rule="r1")

    def test_all_mode_passed(self) -> None:
        assert points_fn(self._make_result(1.0, True), "ALL", 10.0) == 10.0

    def test_all_mode_failed(self) -> None:
        assert points_fn(self._make_result(0.0, False), "ALL", 10.0) == 0.0

    def test_any_mode_passed(self) -> None:
        assert points_fn(self._make_result(1.0, True), "ANY", 5.0) == 5.0

    def test_partial_mode_proportional(self) -> None:
        assert points_fn(self._make_result(0.75, True), "PARTIAL", 20.0) == 15.0

    def test_non_float_output_raises(self) -> None:
        r = Result(output=True, passed=True, feedback="", rule="r1")
        with pytest.raises(ValueError, match="must be a float"):
            points_fn(r, "ALL", 10.0)

    def test_unsupported_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported aggregation mode"):
            points_fn(self._make_result(1.0, True), "BAD", 10.0)  # type: ignore[arg-type]
