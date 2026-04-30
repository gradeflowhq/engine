import pytest
from pydantic import ValidationError

from gradeflow_engine.exceptions import (
    ConfigurationError,
    QuestionInferenceError,
    QuestionSetValidationError,
)
from gradeflow_engine.question_sets import inference
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models.choice import ChoiceQuestion
from gradeflow_engine.questions.models.multi_valued import MultiValuedQuestion
from gradeflow_engine.questions.models.numeric import NumericQuestion
from gradeflow_engine.questions.models.text import TextQuestion
from gradeflow_engine.submissions.models import RawSubmission


def make_rs(student_id: str, answers: dict[str, str]) -> RawSubmission:
    return RawSubmission(student_id=student_id, raw_answer_map=answers)


def _validation_error() -> ValidationError:
    with pytest.raises(ValidationError) as exc_info:
        TextQuestion.model_validate({"max_points": "not-a-number"})
    return exc_info.value


def test_infer_empty_submissions_returns_empty_question_set() -> None:
    qs = QuestionSet.infer([])
    assert isinstance(qs, QuestionSet)
    assert qs.question_map == {}


def test_infer_choice_when_distinct_values_leq_6_options_autopopulated() -> None:
    subs = [
        make_rs("s1", {"q1": "red, blue, green"}),
        make_rs("s2", {"q1": "blue , yellow"}),
        make_rs("s3", {"q1": "green, purple"}),
        make_rs("s4", {"q1": "red, blue"}),
        make_rs("s5", {"q1": "yellow"}),
    ]
    qs = QuestionSet.infer(subs)  # default choice_delimiter=","
    q = qs.question_map["q1"]
    assert isinstance(q, ChoiceQuestion)
    assert q.options == {"red", "blue", "green", "yellow", "purple"}
    parsed = q.parse("blue,  yellow ,  purple")
    assert parsed == {"blue", "yellow", "purple"}


def test_infer_choice_respects_choice_delimiter() -> None:
    subs = [
        make_rs("s1", {"q1": "A|B|C"}),
        make_rs("s2", {"q1": "B|D"}),
        make_rs("s3", {"q1": "C|E|A"}),
    ]
    qs = QuestionSet.infer(subs, choice_delimiter="|", choice_normalize_case=True)
    q = qs.question_map["q1"]
    assert isinstance(q, ChoiceQuestion)
    assert q.options == {"a", "b", "c", "d", "e"}
    assert q.parse("B|E|A") == {"b", "e", "a"}


def test_infer_multi_valued_when_consistent_cardinality() -> None:
    # All non-empty answers have exactly 2 tokens using ";"
    subs = [
        make_rs("s1", {"q2": "x; y"}),
        make_rs("s2", {"q2": "a; b"}),
        make_rs("s3", {"q2": "  c ;  d  "}),
        make_rs("s4", {"q2": ""}),  # empty ignored in cardinality check
    ]
    qs = QuestionSet.infer(subs, multi_value_delimiter=";")
    q = qs.question_map["q2"]
    assert isinstance(q, MultiValuedQuestion)
    # Ensure the inferred parser uses the provided multi_value_delimiter
    parsed = q.parse("m; n")
    assert parsed == ["m", "n"]


def test_infer_not_multi_valued_when_inconsistent_cardinality() -> None:
    # Inconsistent cardinality: 3 tokens, then 2 tokens -> not MultiValued
    subs = [
        make_rs("s1", {"qmv": "x; y; z"}),
        make_rs("s2", {"qmv": "a; b"}),
        make_rs("s3", {"qmv": "c1"}),
        make_rs("s4", {"qmv": "c2"}),
        make_rs("s5", {"qmv": "c3"}),
        make_rs("s6", {"qmv": "c4"}),
    ]
    qs = QuestionSet.infer(subs, multi_value_delimiter=";", choice_option_limit=5)
    q = qs.question_map["qmv"]
    # With no numeric majority and no single-token choice candidates, fallback is Text
    assert isinstance(q, TextQuestion)


def test_infer_numeric_when_majority_single_tokens_are_numeric() -> None:
    subs = [
        make_rs("s1", {"q3": "42"}),
        make_rs("s2", {"q3": "3.14"}),
        make_rs("s3", {"q3": "100"}),
        make_rs("s4", {"q3": "N/A"}),
        make_rs("s5", {"q3": "text"}),
    ]
    qs = QuestionSet.infer(subs)
    q = qs.question_map["q3"]
    assert isinstance(q, NumericQuestion)
    assert q.parse("15") == 15
    assert q.parse("2.5") == 2.5


def test_infer_text_fallback_when_none_of_the_conditions_match() -> None:
    subs = [
        make_rs("s1", {"q4": "alpha"}),
        make_rs("s2", {"q4": "beta"}),
        make_rs("s3", {"q4": "gamma"}),
        make_rs("s4", {"q4": "delta"}),
        make_rs("s5", {"q4": "epsilon"}),
        make_rs("s6", {"q4": "zeta"}),
        make_rs("s7", {"q4": "eta"}),
    ]
    qs = QuestionSet.infer(subs, choice_option_limit=5)
    q = qs.question_map["q4"]
    assert isinstance(q, TextQuestion)
    assert q.parse("Hello World") == "Hello World"


def test_infer_handles_multiple_questions_in_same_run() -> None:
    subs = [
        make_rs("s1", {"q_choice": "red,blue", "q_multi": "1;2", "q_num": "10", "q_text": "foo"}),
        make_rs("s2", {"q_choice": "blue,green", "q_multi": "3;4", "q_num": "20", "q_text": "bar"}),
        make_rs("s3", {"q_choice": "green", "q_multi": "5;6", "q_num": "30", "q_text": "baz1"}),
        make_rs("s4", {"q_choice": "green", "q_multi": "5;6", "q_num": "1", "q_text": "baz2"}),
        make_rs("s5", {"q_choice": "green", "q_multi": "5;6", "q_num": "2", "q_text": "baz3"}),
        make_rs("s6", {"q_choice": "green", "q_multi": "5;6", "q_num": "3", "q_text": "baz4"}),
        make_rs("s7", {"q_choice": "green", "q_multi": "5;6", "q_num": "4", "q_text": "baz5"}),
    ]
    qs = QuestionSet.infer(
        subs, choice_delimiter=",", multi_value_delimiter=";", choice_option_limit=5
    )

    assert isinstance(qs.question_map["q_choice"], ChoiceQuestion)
    assert qs.question_map["q_choice"].options == {"red", "blue", "green"}

    # Consistent pairs -> MultiValued
    assert isinstance(qs.question_map["q_multi"], MultiValuedQuestion)
    # Numeric majority for q_num: 2 numeric vs 1 non-numeric -> Numeric
    assert isinstance(qs.question_map["q_num"], NumericQuestion)
    assert isinstance(qs.question_map["q_text"], TextQuestion)


def test_parse_with_inferred_question_set() -> None:
    subs = [
        make_rs("s1", {"qid": "A|B|C"}),
        make_rs("s2", {"qid": "B|C"}),
    ]
    qs = QuestionSet.infer(subs, choice_delimiter="|", choice_normalize_case=False)
    new_subs = [
        make_rs("s10", {"qid": "A|C"}),
        make_rs("s11", {"qid": "C"}),
    ]
    parsed = qs.parse(new_subs)
    assert len(parsed) == 2
    assert parsed[0].student_id == "s10"
    assert parsed[0].answer_map["qid"] == {"A", "C"}
    assert parsed[1].answer_map["qid"] == {"C"}


def test_infer_choice_allows_multiple_when_counts_not_all_single_token() -> None:
    # Observed values <= default option limit and some submissions contain multiple tokens
    subs = [
        make_rs("s1", {"qm": "red, blue"}),
        make_rs("s2", {"qm": "blue"}),
        make_rs("s3", {"qm": "red, green"}),
    ]
    qs = QuestionSet.infer(subs)  # default delimiters
    q = qs.question_map["qm"]
    assert isinstance(q, ChoiceQuestion)
    assert q.allow_multiple is True
    assert q.parse("red, blue") == {"red", "blue"}


def test_question_inference_helper_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = inference.MultiValuedParserConfig(delimiter="|")

    assert inference._get_numeric_answers(["", "no", "3"]) == [3]
    assert inference._is_numeric_token("") is False
    assert inference._is_numeric_token("no") is False
    assert inference._infer_value_types_for_positions(["1|", "too-short"], cfg, 2) == [
        "NUMERIC",
        "TEXT",
    ]
    assert inference._get_observed_values(["", "|A|"], cfg) == {"A"}

    inferred = inference._infer_question_for_qid(
        [],
        choice_delimiter=",",
        choice_option_limit=5,
        choice_normalize_case=True,
        multi_value_delimiter="|",
        empty_marker="N/A",
    )
    assert isinstance(inferred, TextQuestion)

    validation_error = _validation_error()
    monkeypatch.setattr(
        inference,
        "_infer_question_for_qid",
        lambda *args, **kwargs: (_ for _ in ()).throw(validation_error),
    )
    with pytest.raises(QuestionSetValidationError):
        inference.infer_question_map([RawSubmission(student_id="s1", raw_answer_map={"Q1": "x"})])

    monkeypatch.setattr(
        inference,
        "_infer_question_for_qid",
        lambda *args, **kwargs: (_ for _ in ()).throw(ConfigurationError("bad")),
    )
    with pytest.raises(ConfigurationError):
        inference.infer_question_map([RawSubmission(student_id="s1", raw_answer_map={"Q1": "x"})])

    monkeypatch.setattr(
        inference,
        "_infer_question_for_qid",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad")),
    )
    with pytest.raises(QuestionInferenceError):
        inference.infer_question_map([RawSubmission(student_id="s1", raw_answer_map={"Q1": "x"})])
