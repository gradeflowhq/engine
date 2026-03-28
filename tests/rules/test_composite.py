import pytest

from gradeflow_engine.rules.models.composite import CompositeQuestionRule, CompositeRule
from gradeflow_engine.rules.models.keywords import KeywordsRule
from gradeflow_engine.rules.models.length import LengthRule
from gradeflow_engine.rules.models.numeric_range import NumericRangeRule
from gradeflow_engine.rules.models.text_match import TextMatchRule


def test_composite_all_mode_matches_and_points() -> None:
    kw = KeywordsRule(keywords=["foo", "bar"], mode="ALL")
    ln = LengthRule(min_length=3, max_length=20)
    comp = CompositeRule(rules=[kw, ln], aggregation="ALL")

    result = comp.process_answer("foo and bar")
    assert result.passed is True
    assert result.output == 1.0
    assert "contains all keywords" in result.feedback

    qcomp = CompositeQuestionRule(question_id="q", rules=[kw, ln], aggregation="ALL")
    qres = qcomp.process_submission({"q": "foo bar"}, {"q": 8.0})["q"]
    assert qres.points == 8.0


def test_composite_any_mode_passes_when_one_subrule_passes() -> None:
    kw = KeywordsRule(keywords=["hello"], mode="ALL")
    ln = LengthRule(min_length=20)
    comp = CompositeRule(rules=[kw, ln], aggregation="ANY")

    result = comp.process_answer("hello world")
    assert result.passed is True
    assert result.output == 1.0

    qcomp = CompositeQuestionRule(question_id="q", rules=[kw, ln], aggregation="ANY")
    qres = qcomp.process_submission({"q": "hello"}, {"q": 10.0})["q"]
    assert qres.points == 10.0


def test_composite_any_mode_all_fail() -> None:
    kw = KeywordsRule(keywords=["x"], mode="ALL")
    ln = LengthRule(min_length=100)
    comp = CompositeRule(rules=[kw, ln], aggregation="ANY")

    result = comp.process_answer("no match here")
    assert result.passed is False
    assert result.output == 0.0


def test_composite_partial_mode_fractional_three_rules() -> None:
    # 3 subrules, 1 passes -> output should be 1/3
    r1 = TextMatchRule(answers=["a"])
    r2 = TextMatchRule(answers=["b"])
    r3 = TextMatchRule(answers=["c"])
    comp = CompositeRule(rules=[r1, r2, r3], aggregation="PARTIAL")

    res = comp.process_answer("a")
    assert abs(res.output - (1.0 / 3.0)) < 1e-9
    assert res.passed is True  # PARTIAL treated like ANY for passed_fn

    qcomp = CompositeQuestionRule(question_id="q", rules=[r1, r2, r3], aggregation="PARTIAL")
    qres = qcomp.process_submission({"q": "a"}, {"q": 9.0})["q"]
    assert abs(qres.points - 3.0) < 1e-9


def test_composite_feedback_concatenation() -> None:
    kw = KeywordsRule(keywords=["foo"], mode="ALL")
    ln = LengthRule(min_length=1)
    comp = CompositeRule(rules=[kw, ln], aggregation="ALL")

    res = comp.process_answer("foo")
    # Feedback should contain both subrule feedbacks
    assert "contains all keywords" in res.feedback
    assert "The answer length is" in res.feedback


def test_composite_exception_propagation_from_subrule() -> None:
    # NumericRangeRule will assert on non-numeric input (in its implementation it may raise)
    nr = NumericRangeRule(min_value=1, max_value=10)
    em = TextMatchRule(answers=["yes"])
    comp = CompositeRule(rules=[em, nr], aggregation="ALL")

    # Passing a non-numeric string should cause NumericRangeRule to raise/assert inside it.
    with pytest.raises(TypeError):
        _ = comp.process_answer("yes")


def test_length_boundaries_and_mixed_types() -> None:
    # length at exact min/max boundaries
    ln = LengthRule(min_length=3, max_length=5)
    kw = KeywordsRule(keywords=["ok"], mode="ALL")
    comp = CompositeRule(rules=[ln, kw], aggregation="ALL")

    res_ok = comp.process_answer("ok!")  # length 3, contains keyword 'ok'
    assert res_ok.passed is True

    res_toolong = comp.process_answer("ok!!!!!")  # length > 5
    assert res_toolong.passed is False
