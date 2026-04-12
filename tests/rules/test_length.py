from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.length import LengthQuestionRule, LengthRule


def test_length_too_short() -> None:
    rule = LengthRule(min_length=5)
    result = rule.process_answer("hey")

    assert result.output is False
    assert result.passed is False
    assert "shorter than the minimum" in result.feedback


def test_length_too_long() -> None:
    rule = LengthRule(max_length=4)
    result = rule.process_answer("abcdef")

    assert result.output is False
    assert result.passed is False
    assert "longer than the maximum" in result.feedback


def test_length_within_range_and_points() -> None:
    rule = LengthRule(min_length=2, max_length=5)
    result = rule.process_answer("hey")

    assert result.output is True
    assert result.passed is True

    qrule = LengthQuestionRule(question_id="q1", min_length=2, max_length=5)
    submission: dict[QuestionId, Answer] = {"q1": "hey"}
    qresult = qrule.process_submission(submission, {"q1": 2.0})["q1"]

    assert qresult.points == 2.0
    assert qresult.max_points == 2.0


def test_length_min_only_pass_and_fail() -> None:
    rule = LengthRule(min_length=3)
    res_pass = rule.process_answer("hey")
    assert res_pass.passed is True

    res_fail = rule.process_answer("no")
    assert res_fail.passed is False


def test_length_max_only_pass_and_fail() -> None:
    rule = LengthRule(max_length=3)
    res_pass = rule.process_answer("hey")
    assert res_pass.passed is True

    res_fail = rule.process_answer("toolong")
    assert res_fail.passed is False


def test_length_exact_length() -> None:
    rule = LengthRule(min_length=4, max_length=4)
    assert rule.process_answer("four").passed is True
    assert rule.process_answer("five!").passed is False


def test_length_question_rule_min_only_points() -> None:
    qrule = LengthQuestionRule(question_id="q2", min_length=2)
    submission: dict[QuestionId, Answer] = {"q2": "ok"}
    qresult = qrule.process_submission(submission, {"q2": 1.5})["q2"]
    assert qresult.points == 1.5


def test_length_words_mode() -> None:
    rule = LengthRule(min_length=3, mode="words")
    assert rule.process_answer("one two three").passed is True
    assert rule.process_answer("one two").passed is False


def test_length_words_mode_max() -> None:
    rule = LengthRule(max_length=2, mode="words")
    assert rule.process_answer("one two").passed is True
    assert rule.process_answer("one two three").passed is False


def test_length_no_constraints() -> None:
    rule = LengthRule()
    assert rule.process_answer("anything").passed is True
    assert rule.process_answer("").passed is True


def test_length_empty_answer_none() -> None:
    rule = LengthRule(min_length=1)
    result = rule.process_answer(None)
    assert result.passed is False
    assert "No answer provided" in result.feedback


def test_length_description_branches() -> None:
    assert "Between" in LengthRule(min_length=1, max_length=5).description
    assert "At least" in LengthRule(min_length=3).description
    assert "At most" in LengthRule(max_length=10).description
    assert "No length" in LengthRule().description
