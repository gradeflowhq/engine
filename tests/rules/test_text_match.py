from gradeflow_engine.questions.models.text import TextQuestion
from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.text_match import (
    TextMatchQuestionRule,
    TextMatchRule,
)


def test_text_match_text_answer() -> None:
    rule = TextMatchRule(answers=["Paris"])
    # TextAnswer is a plain str in this codebase
    result = rule.process_answer("Paris")

    assert result.output is True
    assert "matches one of the correct answer" in result.feedback
    assert result.rule == "TextMatchRule"


def test_non_match_text_answer() -> None:
    rule = TextMatchRule(answers=["Paris"])
    result = rule.process_answer("London")

    assert result.output is False
    assert "does not match" in result.feedback


def test_text_match_numeric_answer() -> None:
    rule = TextMatchRule(answers=["42"])
    # numeric answer as int should compare equal when cast to str
    result = rule.process_answer(42)

    assert result.output is True


def test_text_match_question_rule_points() -> None:
    qrule = TextMatchQuestionRule(question_id="q1", answers=["yes"])
    submission: dict[QuestionId, Answer] = {"q1": "yes"}
    qresult = qrule.process_submission(submission, {"q1": 5.0})["q1"]

    assert qresult.max_points == 5.0
    assert qresult.points == 5.0

    submission = {"q1": "no"}
    qresult = qrule.process_submission(submission, {"q1": 5.0})["q1"]

    assert qresult.points == 0.0


def test_text_match_case_sensitive_string_equality() -> None:
    rule = TextMatchRule(answers=["Paris"])
    assert rule.process_answer("Paris").passed is True
    # different case should fail because equality is exact string match
    assert rule.process_answer("paris").passed is False


def test_text_match_whitespace_sensitive_string_equality() -> None:
    rule = TextMatchRule(answers=["Paris"])
    # leading/trailing whitespace should fail under exact string equality
    assert rule.process_answer(" Paris ").passed is False
    assert rule.process_answer("Paris ").passed is False
    assert rule.process_answer("Paris").passed is True


def test_text_match_numeric_answer_compared_as_string() -> None:
    rule = TextMatchRule(answers=["42"])
    # int 42 -> str(42) == "42" -> match
    assert rule.process_answer(42).passed is True
    # float 42.0 -> str(42.0) == "42.0" -> does not match "42"
    assert rule.process_answer(42.0).passed is False


def test_text_match_fraction_and_formatting() -> None:
    # Accept "1.5" only; different formatting should fail
    rule = TextMatchRule(answers=["1.5"])
    # numeric 1.5 -> str(1.5) == "1.5" -> pass
    assert rule.process_answer(1.5).passed is True
    # text "1.50" vs "1.5" -> fail due to exact string mismatch
    assert rule.process_answer("1.50").passed is False
    # text "3/2" vs "1.5" -> fail: no numeric parsing for string answers; equality is string-based
    assert rule.process_answer("3/2").passed is False


def test_text_match_multiple_acceptables_exact_string_only() -> None:
    rule = TextMatchRule(answers=["YES", "NO"])
    assert rule.process_answer("YES").passed is True
    assert rule.process_answer("NO").passed is True
    # exact string mismatch (case) should fail
    assert rule.process_answer("Yes").passed is False


def test_text_match_question_rule_validation_and_default_max_points() -> None:
    assert (
        TextMatchQuestionRule(question_id="missing", answers=["x"]).validate_compatibility({}) == []
    )
    assert (
        TextMatchQuestionRule(question_id="Q1", answers=["x"])
        .process_submission({"Q1": "x"}, {})["Q1"]
        .max_points
        == 1.0
    )
    assert (
        TextMatchQuestionRule(question_id="Q1", answers=["x"]).validate_compatibility(
            {"Q1": TextQuestion()}
        )
        == []
    )
