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
