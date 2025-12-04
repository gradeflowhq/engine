import pytest
from pydantic import ValidationError

from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.conditional import (
    ConditionalMultiQuestionRule,
    check_condition,
)
from gradeflow_engine.rules.models.exact_match import ExactMatchQuestionRule
from gradeflow_engine.rules.models.numeric_range import NumericRangeQuestionRule


def test_check_condition_and_true() -> None:
    # Create fake QuestionResult-like objects by using NumericRangeQuestionRule processing
    r1 = NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10).process_submission(
        {"q1": 5}
    )
    r2 = NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10).process_submission(
        {"q2": 1}
    )

    assert check_condition([r1, r2], aggregation="AND") is True


def test_check_condition_and_false() -> None:
    r1 = NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10).process_submission(
        {"q1": 5}
    )
    r2 = NumericRangeQuestionRule(
        question_id="q2", min_value=100, max_value=200
    ).process_submission({"q2": 1})

    assert check_condition([r1, r2], aggregation="AND") is False


def test_check_condition_or() -> None:
    r1 = NumericRangeQuestionRule(
        question_id="q1", min_value=100, max_value=200
    ).process_submission({"q1": 5})
    r2 = NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10).process_submission(
        {"q2": 1}
    )

    assert check_condition([r1, r2], aggregation="OR") is True


def test_check_condition_unknown_raises() -> None:
    r = NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10).process_submission(
        {"q1": 5}
    )
    with pytest.raises(ValueError):
        check_condition([r], aggregation="XOR")  # type: ignore


def test_conditional_process_submission_then_branch() -> None:
    # if q1 within range, award points from then_rules
    if_rule = NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=2.0)
    then_rule = ExactMatchQuestionRule(question_id="q2", answers=["yes"], max_points=3.0)
    else_rule = ExactMatchQuestionRule(question_id="q2", answers=["no"], max_points=1.0)

    rule = ConditionalMultiQuestionRule(
        if_rules=[if_rule],
        if_aggregation="AND",
        then_rules=[then_rule],
        else_rules=[else_rule],
    )

    submission: dict[QuestionId, Answer] = {"q1": 5, "q2": "yes"}
    results = rule.process_submission(submission)

    assert len(results) == 1
    assert results[0].question_id == "q2"
    assert results[0].points == 3.0


def test_conditional_process_submission_else_branch() -> None:
    if_rule = NumericRangeQuestionRule(
        question_id="q1", min_value=100, max_value=200, max_points=2.0
    )
    then_rule = ExactMatchQuestionRule(question_id="q2", answers=["yes"], max_points=3.0)
    else_rule = ExactMatchQuestionRule(question_id="q2", answers=["no"], max_points=1.0)

    rule = ConditionalMultiQuestionRule(
        if_rules=[if_rule],
        if_aggregation="AND",
        then_rules=[then_rule],
        else_rules=[else_rule],
    )

    submission: dict[QuestionId, Answer] = {"q1": 5, "q2": "no"}
    results = rule.process_submission(submission)

    assert len(results) == 1
    assert results[0].question_id == "q2"
    assert results[0].points == 1.0


def test_conditional_missing_question_raises() -> None:
    if_rule = NumericRangeQuestionRule(question_id="q_missing", min_value=0, max_value=1)
    then_rule = ExactMatchQuestionRule(question_id="q2", answers=["yes"])
    rule = ConditionalMultiQuestionRule(if_rules=[if_rule], then_rules=[then_rule], else_rules=[])

    with pytest.raises(ValueError):
        rule.process_submission({})


def test_or_aggregation_with_multiple_if_rules() -> None:
    # OR aggregation should pass if any if_rule passes
    if1 = NumericRangeQuestionRule(question_id="q1", min_value=100, max_value=200)
    if2 = NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10)
    then_rule = ExactMatchQuestionRule(question_id="q3", answers=["ok"], max_points=2.0)

    rule = ConditionalMultiQuestionRule(
        if_rules=[if1, if2], if_aggregation="OR", then_rules=[then_rule], else_rules=[]
    )

    submission: dict[QuestionId, Answer] = {"q1": 5, "q2": 5, "q3": "ok"}
    results = rule.process_submission(submission)

    assert len(results) == 1
    assert results[0].question_id == "q3"


def test_multiple_then_rules_return_multiple_results() -> None:
    if_rule = NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10)
    then1 = ExactMatchQuestionRule(question_id="q2", answers=["a"], max_points=1.0)
    then2 = ExactMatchQuestionRule(question_id="q3", answers=["b"], max_points=1.5)

    rule = ConditionalMultiQuestionRule(
        if_rules=[if_rule], then_rules=[then1, then2], else_rules=[]
    )

    submission: dict[QuestionId, Answer] = {"q1": 5, "q2": "a", "q3": "b"}
    results = rule.process_submission(submission)

    assert {r.question_id for r in results} == {"q2", "q3"}


def test_else_rules_empty_returns_empty_list_when_condition_false() -> None:
    if_rule = NumericRangeQuestionRule(question_id="q1", min_value=100, max_value=200)
    # model requires then_rules to be non-empty, provide a dummy then_rule that won't be used
    then_dummy = ExactMatchQuestionRule(question_id="q_dummy", answers=["x"])
    rule = ConditionalMultiQuestionRule(if_rules=[if_rule], then_rules=[then_dummy], else_rules=[])

    submission: dict[QuestionId, Answer] = {"q1": 5}
    results = rule.process_submission(submission)

    # condition is false and else_rules is empty -> should return empty list
    assert results == []


def test_if_rules_min_length_validation() -> None:
    # pydantic should enforce min_length=1 for if_rules and then_rules.
    # constructing with empty list raises ValidationError
    with pytest.raises(ValidationError):
        ConditionalMultiQuestionRule(if_rules=[], then_rules=[], else_rules=[])
