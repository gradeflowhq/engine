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


def test_keywords_empty_answer_returns_no_answer() -> None:
    rule = KeywordsRule(keywords=["foo"])
    result = rule.process_answer(None)
    assert result.passed is False
    assert "No answer provided" in result.feedback


def test_keywords_substring_matching() -> None:
    rule = KeywordsRule(keywords=["bar"], mode="ALL")
    # "bar" is a substring of "embarrass"
    result = rule.process_answer("embarrass")
    assert result.passed is True


def test_keywords_case_sensitive() -> None:
    rule = KeywordsRule(keywords=["Foo"], mode="ALL")
    result = rule.process_answer("foo")
    assert result.passed is False

    result2 = rule.process_answer("Foo")
    assert result2.passed is True


def test_keywords_description_modes() -> None:
    all_rule = KeywordsRule(keywords=["a", "b"], mode="ALL")
    assert "all" in all_rule.description.lower()

    any_rule = KeywordsRule(keywords=["a", "b"], mode="ANY")
    assert "at least one" in any_rule.description.lower()

    partial_rule = KeywordsRule(keywords=["a", "b"], mode="PARTIAL")
    assert "partial" in partial_rule.description.lower()
