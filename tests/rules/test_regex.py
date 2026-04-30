from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.regex import (
    RegexConfig,
    RegexQuestionRule,
    RegexRule,
)


def test_regex_basic_match_and_feedback() -> None:
    rule = RegexRule(pattern=r"^Hello\s+World$")
    result = rule.process_answer("Hello   World")

    assert result.output is True
    assert result.passed is True
    assert "matches" in result.feedback
    assert result.rule == "RegexRule"


def test_regex_no_match() -> None:
    rule = RegexRule(pattern=r"^Hello\s+World$")
    result = rule.process_answer("HelloWorld")

    assert result.output is False
    assert result.passed is False


def test_regex_ignore_case_flag() -> None:
    cfg = RegexConfig(ignore_case=True)
    rule = RegexRule(pattern=r"^hello$", config=cfg)
    result = rule.process_answer("HELLO")

    assert result.output is True


def test_regex_case_sensitive_fails() -> None:
    cfg = RegexConfig(ignore_case=False)
    rule = RegexRule(pattern=r"^hello$", config=cfg)
    result = rule.process_answer("HELLO")

    assert result.output is False


def test_regex_question_rule_points_and_flags() -> None:
    cfg = RegexConfig(multi_line=True, dotall=True)
    qrule = RegexQuestionRule(question_id="q1", pattern=r"^start.*end$", config=cfg)
    submission: dict[QuestionId, Answer] = {"q1": "start\nmiddle\nend"}
    qresult = qrule.process_submission(submission, {"q1": 2.5})["q1"]

    assert qresult.max_points == 2.5
    assert qresult.points == 2.5


def test_regex_multi_line_only() -> None:
    cfg = RegexConfig(multi_line=True, dotall=False)
    # ^ and $ should match start/end of lines when multi_line=True
    rule = RegexRule(pattern=r"^middle$", config=cfg)
    result = rule.process_answer("start\nmiddle\nend")

    assert result.output is True


def test_regex_multi_line_fails_when_disabled() -> None:
    cfg = RegexConfig(multi_line=False, dotall=False)
    rule = RegexRule(pattern=r"^middle$", config=cfg)
    result = rule.process_answer("start\nmiddle\nend")

    assert result.output is False


def test_regex_dotall_only() -> None:
    cfg = RegexConfig(multi_line=False, dotall=True)
    # dotall lets . match newlines
    rule = RegexRule(pattern=r"start.*end", config=cfg)
    result = rule.process_answer("start\nend")

    assert result.output is True


def test_regex_dotall_fails_when_disabled() -> None:
    cfg = RegexConfig(multi_line=False, dotall=False)
    rule = RegexRule(pattern=r"start.*end", config=cfg)
    result = rule.process_answer("start\nend")

    assert result.output is False


def test_regex_description_lists_enabled_flags() -> None:
    regex = RegexRule(
        pattern="x",
        config=RegexConfig(ignore_case=True, multi_line=True, dotall=True),
    )
    assert "ignoring case, multi-line mode, dot matches newlines" in regex.description
