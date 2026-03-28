import pytest

from gradeflow_engine.adapters.raw_submissions.csv import ORIGINAL_POINTS_RULE_NAME
from gradeflow_engine.question_sets.model import QuestionSet, parse_raw_submission
from gradeflow_engine.questions.models import ChoiceQuestion, TextQuestion
from gradeflow_engine.questions.models.multi_valued import MultiValuedQuestion
from gradeflow_engine.questions.models.numeric import NumericQuestion
from gradeflow_engine.questions.parser import MultiValuedParserConfig
from gradeflow_engine.rules.result import QuestionResult
from gradeflow_engine.submissions.models import RawSubmission


def test_parse_answer_map_and_submission_basic() -> None:
    q1 = TextQuestion(description="t1")
    q2 = ChoiceQuestion(description="c1")
    qs = QuestionSet(question_map={"q1": q1, "q2": q2})

    raw_map = {"q1": "hello", "q2": "a,b"}
    raw_sub = RawSubmission(student_id="s1", raw_answer_map=raw_map)
    parsed_list = qs.parse([raw_sub])
    assert len(parsed_list) == 1
    parsed = parsed_list[0]
    assert parsed.student_id == "s1"
    assert parsed.answer_map["q1"] == "hello"
    assert parsed.answer_map["q2"] == {"a", "b"}


def test_questionset_parse_with_configured_choice_parser() -> None:
    # Configure choice question to split on '|' and normalize case
    cfg = MultiValuedParserConfig(delimiter="|", normalize_case=True)
    q1 = TextQuestion(description="t1")
    q2 = ChoiceQuestion(description="c1", config=cfg)
    qs = QuestionSet(question_map={"q1": q1, "q2": q2})

    raw = RawSubmission(student_id="s2", raw_answer_map={"q1": "X", "q2": "A|b| C "})
    parsed_list = qs.parse([raw])
    assert len(parsed_list) == 1
    parsed = parsed_list[0]
    assert parsed.student_id == "s2"
    # ensure choice parsing normalized case and trimmed whitespace
    assert parsed.answer_map["q2"] == {"a", "b", "c"}


def test_questionset_parse_empty_submissions_returns_empty_list() -> None:
    qs = QuestionSet(question_map={})
    assert qs.parse([]) == []


def test_numeric_question_parse() -> None:
    nq = NumericQuestion(description="num")
    qs = QuestionSet(question_map={"q": nq})
    s1 = RawSubmission(student_id="n1", raw_answer_map={"q": "42"})
    s2 = RawSubmission(student_id="n2", raw_answer_map={"q": "2.25"})
    parsed = qs.parse([s1, s2])
    assert parsed[0].answer_map["q"] == 42
    assert parsed[1].answer_map["q"] == 2.25


def test_multi_valued_question_parse() -> None:
    mv = MultiValuedQuestion(
        description="mv",
        value_types=["NUMERIC", "TEXT", "NUMERIC", "TEXT"],
    )
    qs = QuestionSet(question_map={"m": mv})
    raw = "1, two, 3.0, three"
    parsed = qs.parse([RawSubmission(student_id="m1", raw_answer_map={"m": raw})])[0]
    assert parsed.answer_map["m"] == [1, "two", 3.0, "three"]


def test_parse_raw_submission_corrects_passthrough_max_points_from_question_map() -> None:
    # A passthrough result_map entry from CSV import has max_points set to the raw score (3.5).
    # parse_raw_submission should correct it to the authoritative value from the question map (5.0).
    passthrough_result = QuestionResult(
        output=3.5,
        passed=True,
        feedback="",
        rule=ORIGINAL_POINTS_RULE_NAME,
        points=3.5,
        max_points=3.5,  # raw CSV value — should be corrected during parsing
    )
    raw = RawSubmission(
        student_id="s1",
        raw_answer_map={"q2": "yes"},
        result_map={"q1": passthrough_result},
    )
    question_map = {"q1": TextQuestion(max_points=5.0), "q2": TextQuestion(max_points=2.0)}

    parsed = parse_raw_submission(question_map, raw)

    q1 = parsed.result_map["q1"]
    assert q1.points == pytest.approx(3.5)  # unchanged
    assert q1.max_points == pytest.approx(5.0)  # corrected from question_map
