from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.exact_match import (
    ExactMatchQuestionRule,
    ExactMatchRule,
)


def test_exact_match_text_answer() -> None:
    rule = ExactMatchRule(answers=["Paris"])
    # TextAnswer is a plain str in this codebase
    result = rule.process_answer("Paris")

    assert result.output is True
    assert "matches one of the correct answer" in result.feedback
    assert result.rule == "ExactMatchRule"


def test_non_match_text_answer() -> None:
    rule = ExactMatchRule(answers=["Paris"])
    result = rule.process_answer("London")

    assert result.output is False
    assert "does not match" in result.feedback


def test_exact_match_numeric_answer() -> None:
    rule = ExactMatchRule(answers=["42"])
    # numeric answer as int should compare equal when cast to str
    result = rule.process_answer(42)

    assert result.output is True


def test_exact_match_question_rule_points() -> None:
    qrule = ExactMatchQuestionRule(question_id="q1", answers=["yes"], max_points=5.0)
    submission: dict[QuestionId, Answer] = {"q1": "yes"}
    qresult = qrule.process_submission(submission)

    assert qresult.question_id == "q1"
    assert qresult.max_points == 5.0
    assert qresult.points == 5.0

    submission = {"q1": "no"}
    qresult = qrule.process_submission(submission)

    assert qresult.points == 0.0
