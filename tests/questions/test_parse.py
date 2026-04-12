import pytest

from gradeflow_engine.questions import utils


def test_try_parse_number_int_and_float() -> None:
    assert utils.try_parse_number("7") == 7
    assert utils.try_parse_number("2.5") == 2.5


def test_try_parse_number_fraction() -> None:
    assert utils.try_parse_number("3/4") == 0.75
    assert utils.try_parse_number("1/2") == 0.5


def test_try_parse_number_scientific_notation() -> None:
    assert utils.try_parse_number("1e5") == 100000.0


def test_try_parse_number_negative() -> None:
    assert utils.try_parse_number("-7") == -7
    assert utils.try_parse_number("-2.5") == -2.5


def test_try_parse_number_whitespace() -> None:
    assert utils.try_parse_number("  42  ") == 42


def test_try_parse_number_nan_raises() -> None:
    with pytest.raises(ValueError, match="not a valid value"):
        utils.try_parse_number("nan")


def test_try_parse_number_inf_raises() -> None:
    with pytest.raises(ValueError, match="not finite"):
        utils.try_parse_number("inf")
    with pytest.raises(ValueError, match="not finite"):
        utils.try_parse_number("-inf")


def test_try_parse_number_invalid_raises() -> None:
    with pytest.raises(ValueError):
        utils.try_parse_number("abc")


def test_parse_multi_value_defaults_and_options() -> None:
    s = " a ,b,c "
    assert utils.parse_multi_value(s) == ["a", "b", "c"]
    assert utils.parse_multi_value(s, trim_whitespace=False) == [" a ", "b", "c "]
    assert utils.parse_multi_value("A|B", delimiter="|", normalize_case=True) == [
        "a",
        "b",
    ]


def test_parse_multi_value_single_value() -> None:
    assert utils.parse_multi_value("only") == ["only"]


def test_is_empty_answer() -> None:
    assert utils.is_empty_answer("", "N/A") is True
    assert utils.is_empty_answer("N/A", "N/A") is True
    assert utils.is_empty_answer("hello", "N/A") is False
