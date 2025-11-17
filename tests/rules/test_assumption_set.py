import pytest

from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.assumption_set import (
    Assumption,
    AssumptionSetMultiQuestionRule,
    choose_assumption_result,
    evaluate_assumption,
)
from gradeflow_engine.rules.models.numeric_range import NumericRangeQuestionRule


def test_choose_assumption_result_max_mode() -> None:
    # two assumptions: one gives 1 point, the other gives 0 points
    a1 = Assumption(
        name="a1",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0)
        ],
    )
    a2 = Assumption(
        name="a2",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=100, max_value=200, max_points=1.0)
        ],
    )

    # supply an answer that matches the first assumption but not the second
    answers: dict[QuestionId, Answer] = {"q1": 5}

    ar1 = evaluate_assumption(a1, answers)
    ar2 = evaluate_assumption(a2, answers)

    chosen = choose_assumption_result([ar1, ar2], mode="MAX")

    # chosen should be the one with points=1.0
    assert chosen.assumption.name == "a1"
    assert sum(r.points for r in chosen.question_results) == 1.0


def test_choose_assumption_result_min_mode() -> None:
    # two assumptions: one gives 2 points across two rules, the other gives 1 point
    a1 = Assumption(
        name="a1",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0),
            NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10, max_points=1.0),
        ],
    )
    a2 = Assumption(
        name="a2",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0),
        ],
    )

    answers: dict[QuestionId, Answer] = {"q1": 5, "q2": 5}

    ar1 = evaluate_assumption(a1, answers)
    ar2 = evaluate_assumption(a2, answers)

    chosen = choose_assumption_result([ar1, ar2], mode="MIN")

    # MIN should pick the assumption with fewer total points (a2)
    assert chosen.assumption.name == "a2"
    assert sum(r.points for r in chosen.question_results) == 1.0


def test_assumption_set_process_submission_returns_chosen_question_results() -> None:
    # Build an AssumptionSet rule with two assumptions that target different questions
    a1 = Assumption(
        name="a1",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=2.0)
        ],
    )
    a2 = Assumption(
        name="a2",
        rules=[
            NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10, max_points=3.0)
        ],
    )

    rule = AssumptionSetMultiQuestionRule(assumptions=[a1, a2], mode="MAX")

    # If we provide q2 within range, a2 should be chosen and its QuestionResult returned
    submission: dict[QuestionId, Answer] = {"q1": 100, "q2": 5}
    qresults = rule.process_submission(submission)

    assert len(qresults) == 1
    assert qresults[0].question_id == "q2"
    assert qresults[0].points == 3.0


def test_mixed_rule_types_inside_assumption() -> None:
    # Use an ExactMatch question rule together with NumericRange to ensure heterogeneous rules work
    from gradeflow_engine.rules.models.exact_match import ExactMatchQuestionRule

    a1 = Assumption(
        name="a1",
        rules=[
            ExactMatchQuestionRule(question_id="q1", answer="yes", max_points=2.0),
            NumericRangeQuestionRule(question_id="q2", min_value=0, max_value=10, max_points=1.0),
        ],
    )
    a2 = Assumption(
        name="a2",
        rules=[ExactMatchQuestionRule(question_id="q1", answer="no", max_points=2.0)],
    )

    rule = AssumptionSetMultiQuestionRule(assumptions=[a1, a2], mode="MAX")

    submission: dict[QuestionId, Answer] = {"q1": "yes", "q2": 5}
    qresults = rule.process_submission(submission)

    # a1 should be chosen and both q1 and q2 results returned
    assert len(qresults) == 2
    ids = {r.question_id for r in qresults}
    assert ids == {"q1", "q2"}


def test_missing_answer_raises_value_error() -> None:
    # A rule references q_missing which is not in the submission; process_submission should raise
    a = Assumption(
        name="a",
        rules=[NumericRangeQuestionRule(question_id="q_missing", min_value=0, max_value=1)],
    )
    rule = AssumptionSetMultiQuestionRule(assumptions=[a], mode="MAX")

    with pytest.raises(ValueError):
        rule.process_submission({})


def test_tie_between_assumptions_is_deterministic() -> None:
    # Two assumptions produce the same total points.
    # Python's max will return the first one encountered.
    a1 = Assumption(
        name="a1",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0)
        ],
    )
    a2 = Assumption(
        name="a2",
        rules=[
            NumericRangeQuestionRule(question_id="q1", min_value=0, max_value=10, max_points=1.0)
        ],
    )

    answers: dict[QuestionId, Answer] = {"q1": 5}

    ar1 = evaluate_assumption(a1, answers)
    ar2 = evaluate_assumption(a2, answers)

    chosen = choose_assumption_result([ar1, ar2], mode="MAX")
    # Should pick the first in the list when tied
    assert chosen.assumption.name == "a1"


def test_choose_assumption_result_empty_list_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        choose_assumption_result([], mode="MAX")
