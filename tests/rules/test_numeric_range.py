import pytest

from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.numeric_range import (
    NumericRangeQuestionRule,
    NumericRangeRule,
)


def test_numeric_range_within_range_passes() -> None:
    rule = NumericRangeRule(min_value=10.0, max_value=20.0)
    result = rule.process_answer(15)

    assert result.passed is True


def test_numeric_range_min_only() -> None:
    rule = NumericRangeRule(min_value=5.0, max_value=None)
    assert rule.process_answer(5).passed is True
    assert rule.process_answer(4).passed is False


def test_numeric_range_max_only() -> None:
    rule = NumericRangeRule(min_value=None, max_value=100.0)
    assert rule.process_answer(100).passed is True
    assert rule.process_answer(101).passed is False


def test_numeric_range_below_min_fails() -> None:
    rule = NumericRangeRule(min_value=10.0, max_value=20.0)
    result = rule.process_answer(5)

    assert result.passed is False
    assert "less than the minimum" in result.feedback


def test_numeric_range_at_min_passes() -> None:
    rule = NumericRangeRule(min_value=10.0, max_value=20.0)
    result = rule.process_answer(10.0)

    assert result.passed is True


def test_numeric_range_within_passes() -> None:
    rule = NumericRangeRule(min_value=0, max_value=100)
    result = rule.process_answer(50)

    assert result.passed is True


def test_numeric_range_at_max_passes() -> None:
    rule = NumericRangeRule(min_value=0, max_value=5)
    result = rule.process_answer(5)

    assert result.passed is True


def test_numeric_range_above_max_fails() -> None:
    rule = NumericRangeRule(min_value=0, max_value=10)
    result = rule.process_answer(11)

    assert result.passed is False
    assert "greater than the maximum" in result.feedback


def test_numeric_range_question_rule_points() -> None:
    qrule = NumericRangeQuestionRule(question_id="q1", min_value=1, max_value=3)
    submission: dict[QuestionId, Answer] = {"q1": 2}
    qresult = qrule.process_submission(submission, {"q1": 4.0})["q1"]

    assert qresult.points == 4.0

    submission = {"q1": 5}
    qresult = qrule.process_submission(submission, {"q1": 4.0})["q1"]
    assert qresult.points == 0.0


def test_numeric_range_non_numeric_raises() -> None:
    rule = NumericRangeRule(min_value=0, max_value=10)
    with pytest.raises(TypeError):
        rule.process_answer("not-a-number")


def test_numeric_range_bool_is_not_numeric() -> None:
    rule = NumericRangeRule(min_value=0, max_value=10)
    with pytest.raises(TypeError):
        rule.process_answer(True)


def test_numeric_range_description_variants() -> None:
    assert NumericRangeRule().description == "No numeric range specified."
    assert NumericRangeRule(min_value=1).description.startswith("Greater than")
    assert NumericRangeRule(max_value=2).description.startswith("Less than")
