from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.keywords import KeywordsQuestionRule, KeywordsRule


def test_keywords_all_mode_pass_and_points() -> None:
    rule = KeywordsRule(keywords=["foo", "bar"], mode="ALL")
    result = rule.process_answer("this contains foo and bar")

    assert result.passed is True
    assert result.output == 1.0

    qrule = KeywordsQuestionRule(question_id="q1", keywords=["foo", "bar"], mode="ALL")
    submission: dict[QuestionId, Answer] = {"q1": "foo bar"}
    qresult = qrule.process_submission(submission, {"q1": 4.0})["q1"]

    assert qresult.points == 4.0


def test_keywords_any_mode() -> None:
    rule = KeywordsRule(keywords=["alpha", "beta"], mode="ANY")
    result = rule.process_answer("contains alpha")

    assert result.passed is True
    assert result.output == 1.0

    result2 = rule.process_answer("contains none")
    assert result2.passed is False
    assert result2.output == 0.0


def test_keywords_partial_mode_fractional_points() -> None:
    rule = KeywordsRule(keywords=["one", "two", "three"], mode="PARTIAL")
    result = rule.process_answer("one and three present")

    # two of three present -> output should be 2/3
    assert abs(result.output - (2.0 / 3.0)) < 1e-9
    assert result.passed is True

    qrule = KeywordsQuestionRule(
        question_id="q2",
        keywords=["one", "two", "three"],
        mode="PARTIAL",
    )
    submission: dict[QuestionId, Answer] = {"q2": "one three"}
    qresult = qrule.process_submission(submission, {"q2": 9.0})["q2"]

    # points should be 9 * (2/3) = 6.0
    assert abs(qresult.points - 6.0) < 1e-9
