import pytest

from gradeflow_engine.questions.models.numeric import NumericQuestion


def test_numeric_parses_int_and_float() -> None:
    q = NumericQuestion()
    assert q.parse("10") == 10
    assert q.parse("3.14") == 3.14


def test_numeric_raises_on_invalid() -> None:
    q = NumericQuestion()
    with pytest.raises(ValueError):
        q.parse("not-a-number")


def test_numeric_parses_fraction() -> None:
    q = NumericQuestion()
    assert q.parse("3/4") == 0.75


def test_numeric_parses_scientific_notation() -> None:
    q = NumericQuestion()
    assert q.parse("1e3") == 1000.0


def test_numeric_parses_negative() -> None:
    q = NumericQuestion()
    assert q.parse("-7") == -7


def test_numeric_empty_marker_returns_none() -> None:
    q = NumericQuestion()
    assert q.parse("N/A") is None
    assert q.parse("") is None
