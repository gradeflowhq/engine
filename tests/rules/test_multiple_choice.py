from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.multiple_choice import (
    MultipleChoiceQuestionRule,
    MultipleChoiceRule,
)


def test_multiple_choice_all_mode_exact_match() -> None:
    rule = MultipleChoiceRule(answer={"A", "B"}, mode="ALL")
    result = rule.process_answer({"A", "B"})

    assert result.passed is True
    assert result.output == 1


def test_multiple_choice_all_mode_missing_choice_fails() -> None:
    rule = MultipleChoiceRule(answer={"A", "B"}, mode="ALL")
    result = rule.process_answer({"A"})  # missing B

    assert result.passed is False
    assert result.output == 0


def test_multiple_choice_any_mode_passes_with_one() -> None:
    rule = MultipleChoiceRule(answer={"A", "B"}, mode="ANY")
    result = rule.process_answer({"B", "X"})

    assert result.passed is True
    assert result.output == 1


def test_multiple_choice_partial_mode_fractional_output_and_points() -> None:
    qrule = MultipleChoiceQuestionRule(
        question_id="q", answer={"A", "B", "C"}, mode="PARTIAL", max_points=6.0
    )
    # Provide two correct and one incorrect -> num_correct=2, num_incorrect=1 -> (2-1)/3 = 1/3
    submission: dict[QuestionId, Answer] = {"q": {"A", "B", "X"}}
    qresult = qrule.process_submission(submission)

    # Expect fractional points = 6 * (1/3) = 2.0
    assert abs(qresult.points - 2.0) < 1e-9


def test_multiple_choice_question_rule_all_any_points() -> None:
    q_all = MultipleChoiceQuestionRule(question_id="q1", answer={"A"}, mode="ALL", max_points=5.0)
    res = q_all.process_submission({"q1": {"A"}})
    assert res.points == 5.0

    q_any = MultipleChoiceQuestionRule(
        question_id="q2", answer={"A", "B"}, mode="ANY", max_points=3.0
    )
    res = q_any.process_submission({"q2": {"B"}})
    assert res.points == 3.0
