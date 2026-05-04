import pytest

from gradeflow_engine.questions.models import ChoiceQuestion, TextQuestion
from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.multiple_choice import (
    MultipleChoiceQuestionRule,
    MultipleChoiceRule,
)


def test_multiple_choice_all_mode_text_match() -> None:
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
    qrule = MultipleChoiceQuestionRule(question_id="q", answer={"A", "B", "C"}, mode="PARTIAL")
    # Provide two correct and one incorrect -> num_correct=2, num_incorrect=1 -> (2-1)/3 = 1/3
    submission: dict[QuestionId, Answer] = {"q": {"A", "B", "X"}}
    qresult = qrule.process_submission(submission, {"q": 6.0})["q"]

    # Expect fractional points = 6 * (1/3) = 2.0
    assert abs(qresult.points - 2.0) < 1e-9


def test_multiple_choice_question_rule_all_any_points() -> None:
    q_all = MultipleChoiceQuestionRule(question_id="q1", answer={"A"}, mode="ALL")
    res = q_all.process_submission({"q1": {"A"}}, {"q1": 5.0})["q1"]
    assert res.points == 5.0

    q_any = MultipleChoiceQuestionRule(question_id="q2", answer={"A", "B"}, mode="ANY")
    res = q_any.process_submission({"q2": {"B"}}, {"q2": 3.0})["q2"]
    assert res.points == 3.0


def test_multiple_choice_all_mode_full_match_output_points_feedback_passed() -> None:
    # ALL requires exact match of the correct set
    qrule = MultipleChoiceQuestionRule(
        question_id="q_all",
        answer={"A", "B"},
        mode="ALL",
    )
    res = qrule.process_submission({"q_all": {"A", "B"}}, {"q_all": 4.0})["q_all"]

    assert res.passed is True
    assert res.output == 1.0
    assert res.points == 4.0
    # Feedback should indicate correct choices; no "Incorrect choice(s)." prefix when passed
    assert "Correct choice(s) selected: A, B" in res.feedback
    assert "Incorrect choice(s)." not in res.feedback


def test_multiple_choice_all_mode_incorrect_output_points_feedback_passed() -> None:
    # Missing a required choice -> fail
    qrule = MultipleChoiceQuestionRule(
        question_id="q_all_miss",
        answer={"A", "B"},
        mode="ALL",
    )
    res = qrule.process_submission({"q_all_miss": {"A"}}, {})["q_all_miss"]

    assert res.passed is False
    assert res.output == 0.0
    assert res.points == 0.0
    # Feedback should include the ALL-mode incorrect prefix and indicate not-selected correct
    assert res.feedback.startswith("Incorrect choice(s).")
    assert "Correct choice(s) not selected: B." in res.feedback


def test_multiple_choice_any_mode_pass_with_one_correct() -> None:
    # ANY passes if at least one correct choice is selected
    qrule = MultipleChoiceQuestionRule(
        question_id="q_any",
        answer={"A", "B"},
        mode="ANY",
    )
    res = qrule.process_submission({"q_any": {"B", "X"}}, {"q_any": 5.0})["q_any"]

    assert res.passed is True
    assert res.output == 1.0
    assert res.points == 5.0
    # Feedback should list correct and incorrect selections; no "No correct" prefix when passed
    assert "Correct choice(s) selected: B." in res.feedback
    assert "Incorrect choice(s) selected: X." in res.feedback
    assert "No correct choice(s) were selected." not in res.feedback


def test_multiple_choice_any_mode_fail_with_none_correct() -> None:
    qrule = MultipleChoiceQuestionRule(
        question_id="q_any_fail",
        answer={"A", "B"},
        mode="ANY",
    )
    res = qrule.process_submission({"q_any_fail": {"X"}}, {})["q_any_fail"]

    assert res.passed is False
    assert res.output == 0.0
    assert res.points == 0.0
    # Feedback should start with ANY-mode failure message
    assert res.feedback.startswith("No correct choice(s) were selected.")


def test_multiple_choice_partial_mode_fractional_output_points_feedback_passed() -> None:
    # Correct set has 3; student picks 2 correct and 1 incorrect -> (2 - 1) / 3 = 1/3
    qrule = MultipleChoiceQuestionRule(
        question_id="q_part",
        answer={"A", "B", "C"},
        mode="PARTIAL",
    )
    res = qrule.process_submission({"q_part": {"A", "B", "X"}}, {"q_part": 9.0})["q_part"]

    assert res.passed is True  # at least one correct selected -> passed True for PARTIAL
    assert pytest.approx(res.output) == (1.0 / 3.0)
    assert pytest.approx(res.points) == 3.0  # 9 * (1/3)
    # Feedback includes Partial credit formula and details of correct/incorrect/not-selected
    assert "Partial credit: (2 - 1) / 3 * max points (minimum: 0)." in res.feedback
    assert "Correct choice(s) selected: A, B." in res.feedback
    assert "Incorrect choice(s) selected: X." in res.feedback
    assert "Correct choice(s) not selected: C." in res.feedback


def test_multiple_choice_partial_mode_all_incorrect_zero_output_points_fail() -> None:
    # No correct choices selected -> (0 - k)/n clipped to 0; fail and 0 points
    qrule = MultipleChoiceQuestionRule(
        question_id="q_part_fail",
        answer={"A", "B"},
        mode="PARTIAL",
    )
    res = qrule.process_submission({"q_part_fail": {"X", "Y"}}, {})["q_part_fail"]

    assert res.passed is False
    assert res.output == 0.0
    assert res.points == 0.0
    # Feedback should contain Partial credit line and mention not-selected correct choices
    assert "Partial credit:" in res.feedback
    assert "Correct choice(s) not selected: A, B." in res.feedback


def test_multiple_choice_rule_output_and_feedback_without_points() -> None:
    # Base rule (non-question) tests output and feedback only
    rule_all = MultipleChoiceRule(answer={"A", "B"}, mode="ALL")
    res_all = rule_all.process_answer({"A"})
    assert res_all.output == 0.0
    assert res_all.passed is False
    assert res_all.feedback.startswith("Incorrect choice(s).")

    rule_any = MultipleChoiceRule(answer={"A", "B"}, mode="ANY")
    res_any = rule_any.process_answer({"B"})
    assert res_any.output == 1.0
    assert res_any.passed is True
    assert "Correct choice(s) selected: B." in res_any.feedback

    rule_partial = MultipleChoiceRule(answer={"A", "B", "C"}, mode="PARTIAL")

    res_partial = rule_partial.process_answer({"A", "X"})
    # num_correct=1, num_incorrect=1 -> max(0, 1-1)/3 = 0.0
    assert res_partial.output == 0.0
    assert res_partial.passed is False
    assert "Partial credit: (1 - 1) / 3 * max points (minimum: 0)." in res_partial.feedback

    res_partial = rule_partial.process_answer({"A", "B"})
    # num_correct=2, num_incorrect=1 -> max(0, 2-1)/3 = 1/3
    assert res_partial.output == pytest.approx(2.0 / 3.0)
    assert res_partial.passed is True
    assert "Partial credit: (2 - 0) / 3 * max points (minimum: 0)." in res_partial.feedback


def test_multiple_choice_defensive_edges() -> None:
    malformed = MultipleChoiceRule.model_construct(answer={"A"}, mode="BAD")
    with pytest.raises(ValueError):
        _ = malformed.description
    with pytest.raises(ValueError):
        malformed._process_answer({"A"})

    assert MultipleChoiceRule(answer={"A"}).validate_question_compatibility(TextQuestion())
    invalid_choice_errors = MultipleChoiceRule(answer={"B"}).validate_question_compatibility(
        ChoiceQuestion(options={"A"})
    )
    assert "Invalid answer choices" in invalid_choice_errors[0]

    with pytest.raises(TypeError):
        MultipleChoiceRule(answer={"A"})._process_answer(["A"])  # type: ignore[arg-type]


def test_multiple_choice_description_variants() -> None:
    assert "at least one" in MultipleChoiceRule(answer={"A"}, mode="ANY").description
    assert "Partial credit" in MultipleChoiceRule(answer={"A"}, mode="PARTIAL").description
