import pytest

from gradeflow_engine.questions.models.multi_valued import MultiValuedQuestion
from gradeflow_engine.questions.models.text import TextQuestion
from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models import SingleTargetRule
from gradeflow_engine.rules.models.multi_valued import (
    MultiValuedQuestionRule,
    MultiValuedRule,
    feedback_fn,
)
from gradeflow_engine.rules.models.numeric_range import NumericRangeRule
from gradeflow_engine.rules.models.text_match import TextMatchRule
from gradeflow_engine.rules.result import Result


def test_multi_valued_all_pass() -> None:
    # All inner rules match -> passed True and full points
    rules: list[SingleTargetRule] = [
        TextMatchRule(answers=["A"]),
        TextMatchRule(answers=["B"]),
    ]
    qrule = MultiValuedQuestionRule(question_id="q", rules=rules, aggregation="ALL")

    submission: dict[QuestionId, Answer] = {"q": ["A", "B"]}
    qresult = qrule.process_submission(submission, {"q": 4.0})["q"]

    assert qresult.points == 4.0
    assert qresult.max_points == 4.0


def test_multi_valued_any_pass() -> None:
    # Only one inner rule matches -> ANY should pass and award full points
    rules: list[SingleTargetRule] = [
        TextMatchRule(answers=["A"]),
        TextMatchRule(answers=["B"]),
    ]
    qrule = MultiValuedQuestionRule(question_id="q", rules=rules, aggregation="ANY")

    submission: dict[QuestionId, Answer] = {"q": ["A", "X"]}
    qresult = qrule.process_submission(submission, {"q": 3.0})["q"]

    assert qresult.points == 3.0
    assert qresult.max_points == 3.0


def test_multi_valued_partial_points() -> None:
    # PARTIAL aggregation returns fractional points
    rules: list[SingleTargetRule] = [
        TextMatchRule(answers=["A"]),
        TextMatchRule(answers=["B"]),
        TextMatchRule(answers=["C"]),
    ]
    qrule = MultiValuedQuestionRule(question_id="q", rules=rules, aggregation="PARTIAL")

    submission: dict[QuestionId, Answer] = {"q": ["A", "X", "C"]}
    qresult = qrule.process_submission(submission, {"q": 6.0})["q"]

    # Two of three matched -> 2/3 of max_points
    assert abs(qresult.points - (6.0 * 2 / 3)) < 1e-6


def test_multi_valued_all_fail() -> None:
    rules: list[SingleTargetRule] = [
        TextMatchRule(answers=["A"]),
        TextMatchRule(answers=["B"]),
    ]
    rule = MultiValuedRule(rules=rules, aggregation="ALL")
    result = rule.process_answer(["X", "Y"])
    assert result.passed is False
    assert result.output == 0.0


def test_multi_valued_length_mismatch_raises_value_error() -> None:
    rules: list[SingleTargetRule] = [TextMatchRule(answers=["A"])]
    rule = MultiValuedRule(rules=rules)
    import pytest

    with pytest.raises(ValueError, match="must match"):
        rule.process_answer(["A", "B"])


def test_multi_valued_non_list_raises_type_error() -> None:
    rules: list[SingleTargetRule] = [TextMatchRule(answers=["A"])]
    rule = MultiValuedRule(rules=rules)
    import pytest

    with pytest.raises(TypeError, match="not compatible"):
        rule.process_answer("not-a-list")


def test_feedback_fn_format() -> None:
    results = [
        Result(output=True, passed=True, feedback="Good", rule="r1"),
        Result(output=False, passed=False, feedback="Bad", rule="r2"),
    ]
    fb = feedback_fn(results)
    assert "[1] Correct" in fb
    assert "[2] Incorrect" in fb
    assert "Good" in fb
    assert "Bad" in fb


def test_multi_valued_description() -> None:
    rules: list[SingleTargetRule] = [
        TextMatchRule(answers=["A"]),
        TextMatchRule(answers=["B"]),
    ]
    rule = MultiValuedRule(rules=rules)
    assert "Value 1" in rule.description
    assert "Value 2" in rule.description


def test_multi_valued_validation_edges() -> None:
    rule = MultiValuedRule(rules=[TextMatchRule(answers=["x"])])
    assert rule.validate_question_compatibility(TextQuestion())
    assert rule.validate_question_compatibility(MultiValuedQuestion(value_types=["TEXT", "TEXT"]))

    inner_error_rule = MultiValuedRule(rules=[NumericRangeRule(min_value=1)])
    errors = inner_error_rule.validate_question_compatibility(
        MultiValuedQuestion(value_types=["TEXT"])
    )
    assert any("Value 0" in error for error in errors)

    with pytest.raises(TypeError):
        rule._process_answer("not a list")
