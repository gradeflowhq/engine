import pytest

from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models.choice import ChoiceQuestion
from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.assumption_set import (
    Assumption,
    AssumptionSetMultiQuestionRule,
    AssumptionSetQuestionRule,
    MultiQuestionAssumption,
    choose_assumption_result,
    evaluate_assumption,
)
from gradeflow_engine.rules.models.exact_match import ExactMatchQuestionRule, ExactMatchRule
from gradeflow_engine.rules.models.length import LengthRule
from gradeflow_engine.rules.models.numeric_range import NumericRangeQuestionRule, NumericRangeRule


def test_choose_assumption_result_max_mode() -> None:
    # two assumptions: one gives 1 point, the other gives 0 points
    a1 = MultiQuestionAssumption(
        name="a1",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0)
        ],
    )
    a2 = MultiQuestionAssumption(
        name="a2",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=100, max_value=200, max_points=1.0)
        ],
    )

    answers: dict[QuestionId, Answer] = {"q1": 5}
    ar1 = evaluate_assumption(a1, answers)
    ar2 = evaluate_assumption(a2, answers)

    chosen = choose_assumption_result([ar1, ar2], mode="MAX")

    assert chosen.assumption.name == "a1"
    assert sum(r.points for r in chosen.question_results) == 1.0


def test_choose_assumption_result_min_mode() -> None:
    # two assumptions: one gives 2 points across two rules, the other gives 1 point
    a1 = MultiQuestionAssumption(
        name="a1",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0),
            NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10, max_points=1.0),
        ],
    )
    a2 = MultiQuestionAssumption(
        name="a2",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0),
        ],
    )

    answers: dict[QuestionId, Answer] = {"q1": 5, "q2": 5}
    ar1 = evaluate_assumption(a1, answers)
    ar2 = evaluate_assumption(a2, answers)

    chosen = choose_assumption_result([ar1, ar2], mode="MIN")

    assert chosen.assumption.name == "a2"
    assert sum(r.points for r in chosen.question_results) == 1.0


def test_assumption_set_process_submission_returns_chosen_question_results() -> None:
    # Build an AssumptionSet rule with two assumptions that target different questions
    a1 = MultiQuestionAssumption(
        name="a1",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=2.0)
        ],
    )
    a2 = MultiQuestionAssumption(
        name="a2",
        rules=[
            NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10, max_points=3.0)
        ],
    )

    rule = AssumptionSetMultiQuestionRule(assumptions=[a1, a2], mode="MAX")

    # q2 within range -> a2 chosen -> return its QuestionResult(s)
    submission: dict[QuestionId, Answer] = {"q1": 100, "q2": 5}
    qresults = rule.process_submission(submission)

    assert len(qresults) == 1
    assert qresults[0].question_id == "q2"
    assert qresults[0].points == 3.0
    # feedback should contain chosen assumption name
    assert "[Assumption: a2]" in qresults[0].feedback


def test_mixed_rule_types_inside_assumption() -> None:
    a1 = MultiQuestionAssumption(
        name="a1",
        rules=[
            ExactMatchQuestionRule(question_id="q1", answers=["yes"], max_points=2.0),
            NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10, max_points=1.0),
        ],
    )
    a2 = MultiQuestionAssumption(
        name="a2",
        rules=[ExactMatchQuestionRule(question_id="q1", answers=["no"], max_points=2.0)],
    )

    rule = AssumptionSetMultiQuestionRule(assumptions=[a1, a2], mode="MAX")

    submission: dict[QuestionId, Answer] = {"q1": "yes", "q2": 5}
    qresults = rule.process_submission(submission)

    assert len(qresults) == 2
    ids = {r.question_id for r in qresults}
    assert ids == {"q1", "q2"}
    assert all("[Assumption: a1]" in r.feedback for r in qresults)


def test_missing_answer_raises_value_error() -> None:
    a = MultiQuestionAssumption(
        name="a",
        rules=[NumericRangeQuestionRule(question_id="q_missing", min_value=0, max_value=1)],
    )
    rule = AssumptionSetMultiQuestionRule(assumptions=[a], mode="MAX")
    with pytest.raises(ValueError):
        rule.process_submission({})


def test_tie_between_assumptions_is_deterministic() -> None:
    a1 = MultiQuestionAssumption(
        name="a1",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0)
        ],
    )
    a2 = MultiQuestionAssumption(
        name="a2",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0)
        ],
    )

    answers: dict[QuestionId, Answer] = {"q1": 5}
    ar1 = evaluate_assumption(a1, answers)
    ar2 = evaluate_assumption(a2, answers)

    chosen = choose_assumption_result([ar1, ar2], mode="MAX")
    assert chosen.assumption.name == "a1"


def test_choose_assumption_result_empty_list_raises() -> None:
    with pytest.raises(ValueError):
        choose_assumption_result([], mode="MAX")


def test_assumption_set_question_rule_max_mode_selects_higher_points() -> None:
    a1 = Assumption(rule=ExactMatchRule(answers=["yes"]), weight=1.0)
    a2 = Assumption(rule=ExactMatchRule(answers=["no"]), weight=0.5)
    rule = AssumptionSetQuestionRule(
        question_id="q1",
        assumptions=[a1, a2],
        mode="MAX",
    )

    submission: dict[QuestionId, Answer] = {"q1": "yes"}
    qresult = rule.process_submission(submission)

    assert qresult.question_id == "q1"
    assert qresult.passed is True
    assert qresult.points == 1.0
    assert qresult.max_points == 1.0


def test_assumption_set_question_rule_min_mode_selects_lower_points_deterministic_on_ties() -> None:
    # Both pass with equal points; MIN should pick deterministically the first assumption
    a_hi = Assumption(name="1", rule=ExactMatchRule(answers=["ok"]))
    a_lo = Assumption(name="2", rule=ExactMatchRule(answers=["ok"]))

    rule = AssumptionSetQuestionRule(
        question_id="q_low",
        assumptions=[a_hi, a_lo],
        mode="MIN",
    )

    submission: dict[QuestionId, Answer] = {"q_low": "ok"}
    qresult = rule.process_submission(submission)

    assert qresult.question_id == "q_low"
    assert qresult.passed is True
    assert qresult.points == 1.0
    assert qresult.max_points == 1.0
    assert "[Assumption: 1]" in qresult.feedback


def test_assumption_set_question_rule_numeric_vs_text_selection() -> None:
    # Mixed inner rule types: ExactMatch vs NumericRange.
    # Provide a numeric answer so the NumericRange assumption passes (ExactMatch fails).
    a_text = Assumption(rule=ExactMatchRule(answers=["five"]))
    a_num = Assumption(rule=NumericRangeRule(min_value=0, max_value=10))

    rule = AssumptionSetQuestionRule(
        question_id="q1",
        assumptions=[a_text, a_num],
        mode="MAX",
    )

    submission: dict[QuestionId, Answer] = {"q1": 5}
    qresult = rule.process_submission(submission)

    assert qresult.question_id == "q1"
    assert qresult.passed is True
    assert qresult.points == 1.0
    assert qresult.max_points == 1.0


def test_assumption_set_question_rule_validate_compatibility_propagates_errors() -> None:
    qset = QuestionSet(question_map={"qC": ChoiceQuestion()})
    a_len = Assumption(rule=LengthRule(min_length=1))
    rule = AssumptionSetQuestionRule(question_id="qC", assumptions=[a_len], mode="MAX")

    errors = rule.validate_compatibility(qset.question_map)
    assert errors, "Expected compatibility errors for TEXT rule against CHOICE question"
    assert any("not compatible" in e for e in errors)


def test_assumption_set_question_rule_missing_answer_raises_value_error() -> None:
    a = Assumption(rule=NumericRangeRule(min_value=0, max_value=1))
    rule = AssumptionSetQuestionRule(question_id="q_missing", assumptions=[a], mode="MAX")
    with pytest.raises(ValueError):
        rule.process_submission({})


def test_assumption_set_question_rule_validate_questions_exist() -> None:
    a = Assumption(rule=ExactMatchRule(answers=["x"]))
    rule = AssumptionSetQuestionRule(question_id="QX", assumptions=[a], mode="MAX")

    errors = rule.validate_questions_exist({"Q1", "Q2"})
    assert errors
    assert any("does not exist" in e for e in errors)

    errors2 = rule.validate_questions_exist({"QX"})
    assert not errors2


def test_assumption_set_question_rule_feedback_includes_assumption_name_for_chosen_MAX() -> None:
    a_yes = Assumption(name="A1-YesCase", rule=ExactMatchRule(answers=["yes"]))
    a_no = Assumption(name="A2-NoCase", rule=ExactMatchRule(answers=["no"]))

    rule = AssumptionSetQuestionRule(
        question_id="q1",
        assumptions=[a_yes, a_no],
        mode="MAX",
    )

    submission: dict[QuestionId, Answer] = {"q1": "yes"}
    qresult = rule.process_submission(submission)

    assert qresult.passed is True
    assert qresult.points == 1.0
    assert qresult.question_id == "q1"
    assert "[Assumption: A1-YesCase]" in qresult.feedback
    assert "[Assumption: A2-NoCase]" not in qresult.feedback


def test_assumption_set_question_rule_feedback_includes_assumption_name_when_other_matches() -> (
    None
):
    a_yes = Assumption(name="A1-YesCase", rule=ExactMatchRule(answers=["yes"]))
    a_no = Assumption(name="A2-NoCase", rule=ExactMatchRule(answers=["no"]))

    rule = AssumptionSetQuestionRule(
        question_id="q1",
        assumptions=[a_yes, a_no],
        mode="MAX",
    )

    submission: dict[QuestionId, Answer] = {"q1": "no"}
    qresult = rule.process_submission(submission)

    assert qresult.passed is True
    assert qresult.points == 1.0
    assert qresult.question_id == "q1"
    assert "[Assumption: A2-NoCase]" in qresult.feedback
    assert "[Assumption: A1-YesCase]" not in qresult.feedback


def test_assumption_set_question_rule_name_omitted_when_none() -> None:
    unnamed = Assumption(name=None, rule=NumericRangeRule(min_value=0, max_value=10))
    rule = AssumptionSetQuestionRule(
        question_id="q_num",
        assumptions=[unnamed],
        mode="MAX",
    )

    submission: dict[QuestionId, Answer] = {"q_num": 5}
    qresult = rule.process_submission(submission)

    assert qresult.passed is True
    assert qresult.points == 1.0
    assert "[Assumption:" not in qresult.feedback


def test_assumption_set_question_rule_weight_scales_points_and_affects_selection() -> None:
    # Both assumptions pass; different weights should affect points and MAX selection
    a_low = Assumption(name="LowW", rule=ExactMatchRule(answers=["ok"]), weight=0.25)
    a_high = Assumption(name="HighW", rule=ExactMatchRule(answers=["ok"]), weight=0.8)

    rule_max = AssumptionSetQuestionRule(question_id="QW", assumptions=[a_low, a_high], mode="MAX")
    rule_min = AssumptionSetQuestionRule(question_id="QW", assumptions=[a_low, a_high], mode="MIN")

    submission: dict[QuestionId, Answer] = {"QW": "ok"}

    # MAX should choose higher weighted points (HighW -> 0.8 * 1.0)
    res_max = rule_max.process_submission(submission)
    assert res_max.points == pytest.approx(0.8)
    assert "[Assumption: HighW]" in res_max.feedback

    # MIN should choose lower weighted points (LowW -> 0.25 * 1.0)
    res_min = rule_min.process_submission(submission)
    assert res_min.points == pytest.approx(0.25)
    assert "[Assumption: LowW]" in res_min.feedback


def test_assumption_set_multi_question_weighting_and_selection() -> None:
    # Two multi-question assumptions, both pass; weights determine MAX selection
    a_low = MultiQuestionAssumption(
        name="LowW",
        weight=0.3,
        rules=[
            NumericRangeQuestionRule(question_id="Q1", min_value=0, max_value=10, max_points=2.0),
            NumericRangeQuestionRule(question_id="Q2", min_value=0, max_value=10, max_points=3.0),
        ],
    )
    a_high = MultiQuestionAssumption(
        name="HighW",
        weight=0.9,
        rules=[
            NumericRangeQuestionRule(question_id="Q1", min_value=0, max_value=10, max_points=1.0),
            NumericRangeQuestionRule(question_id="Q2", min_value=0, max_value=10, max_points=1.0),
        ],
    )

    rule = AssumptionSetMultiQuestionRule(assumptions=[a_low, a_high], mode="MAX")
    submission: dict[QuestionId, Answer] = {"Q1": 5, "Q2": 7}
    results = rule.process_submission(submission)

    # Totals:
    # LowW: (2.0 + 3.0) * 0.3 = 1.5
    # HighW: (1.0 + 1.0) * 0.9 = 1.8 -> chosen
    total_points = sum(r.points for r in results)
    assert total_points == pytest.approx(1.8)
    assert all("[Assumption: HighW]" in r.feedback for r in results)


def test_assumption_weight_bounds_validation() -> None:
    from pydantic import ValidationError

    # Assumption weight out of bounds
    with pytest.raises(ValidationError):
        Assumption(name="BadLow", rule=ExactMatchRule(answers=["x"]), weight=-0.1)

    with pytest.raises(ValidationError):
        Assumption(name="BadHigh", rule=ExactMatchRule(answers=["x"]), weight=1.1)

    # Valid boundary values should be accepted
    Assumption(name="Zero", rule=ExactMatchRule(answers=["x"]), weight=0.0)
    Assumption(name="One", rule=ExactMatchRule(answers=["x"]), weight=1.0)


def test_multi_question_assumption_weight_applies_per_result() -> None:
    # Ensure each QuestionResult within the chosen assumption is individually weighted
    assumption = MultiQuestionAssumption(
        name="W",
        weight=0.5,
        rules=[
            NumericRangeQuestionRule(question_id="Q1", min_value=0, max_value=10, max_points=2.0),
            NumericRangeQuestionRule(question_id="Q2", min_value=0, max_value=10, max_points=4.0),
        ],
    )
    rule = AssumptionSetMultiQuestionRule(assumptions=[assumption], mode="MAX")
    submission: dict[QuestionId, Answer] = {"Q1": 3, "Q2": 7}

    results = rule.process_submission(submission)
    # After weighting: Q1 -> 1.0, Q2 -> 2.0
    pts_by_qid = {r.question_id: r.points for r in results}
    assert pts_by_qid["Q1"] == pytest.approx(1.0)
    assert pts_by_qid["Q2"] == pytest.approx(2.0)
    # Feedback should include the assumption name
    assert all("[Assumption: W]" in r.feedback for r in results)
