import pytest

from gradeflow_engine.authoring import (
    CandidateTestCase,
    execute_candidate_rule,
    get_question_rule_catalog,
    validate_candidate_rule,
)
from gradeflow_engine.exceptions import GradingError, UnknownQuestionError
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models import ChoiceQuestion, TextQuestion
from gradeflow_engine.rubrics.model import Rubric
from gradeflow_engine.rules.models.length import LengthQuestionRule
from gradeflow_engine.rules.models.multiple_choice import MultipleChoiceQuestionRule
from gradeflow_engine.rules.models.text_match import TextMatchQuestionRule
from gradeflow_engine.rules.result import QuestionResult
from gradeflow_engine.rules.schema import (
    GRADEFLOW_INPUT_FIELD,
    GRADEFLOW_KEY,
    GRADEFLOW_SUGGESTIONS_FIELD,
    STRING_LIST_INPUT,
)
from gradeflow_engine.submissions.models import Submission


def _question_set() -> QuestionSet:
    return QuestionSet(
        question_map={
            "q1": TextQuestion(description="Short answer", max_points=2.0),
            "q2": ChoiceQuestion(options={"A", "B"}, max_points=3.0),
        }
    )


def _existing_result(*, points: float = 99.0) -> QuestionResult:
    return QuestionResult(
        points=points,
        max_points=points,
        feedback="Pre-existing result",
        rule="Existing",
        passed=True,
        output=True,
    )


def test_question_rule_catalog_is_compatible_and_contextual() -> None:
    submissions = [
        Submission(student_id="student-1", answer_map={"q1": "yes"}),
        Submission(student_id="student-2", answer_map={"q1": "no"}),
        Submission(student_id="student-3", answer_map={"q1": "yes"}),
    ]
    catalog = get_question_rule_catalog(_question_set(), "q1", submissions=submissions)

    assert catalog.question_id == "q1"
    assert catalog.question_type == "TEXT"
    assert catalog.rules == sorted(catalog.rules, key=lambda entry: entry.type)

    entries = {entry.type: entry for entry in catalog.rules}
    assert "TEXT_MATCH" in entries
    assert "MULTIPLE_CHOICE" not in entries

    text_match = entries["TEXT_MATCH"]
    assert text_match.display_name == "Text Match"
    assert text_match.json_schema["properties"]["question_id"] == {
        "const": "q1",
        "default": "q1",
        "readOnly": True,
        "title": "Question Id",
        "type": "string",
    }
    assert text_match.initial_value["type"] == "TEXT_MATCH"
    assert text_match.initial_value["scope"] == "question"
    assert text_match.initial_value["question_id"] == "q1"
    assert "id" not in text_match.initial_value
    assert text_match.json_schema["properties"]["answers"][GRADEFLOW_KEY] == {
        GRADEFLOW_INPUT_FIELD: STRING_LIST_INPUT,
        GRADEFLOW_SUGGESTIONS_FIELD: {"yes": 2, "no": 1},
    }


def test_question_rule_catalog_rejects_unknown_question() -> None:
    with pytest.raises(UnknownQuestionError):
        get_question_rule_catalog(_question_set(), "missing")


def test_candidate_validation_uses_full_prospective_rubric() -> None:
    question_set = _question_set()
    base_rubric = Rubric(rules=[LengthQuestionRule(question_id="q1", min_length=1, max_length=20)])
    original_rubric = base_rubric.model_copy(deep=True)
    candidate = TextMatchQuestionRule(question_id="q1", answers=["yes"])

    validation = validate_candidate_rule(
        candidate,
        question_set,
        base_rubric=base_rubric,
    )

    assert validation.valid is False
    assert validation.errors == ["Question q1 is targeted by multiple rules: Length, Text Match."]
    assert base_rubric == original_rubric


@pytest.mark.parametrize(
    "candidate, expected_error",
    [
        (
            TextMatchQuestionRule(question_id="missing", answers=["yes"]),
            "Question ID missing does not exist in the assessment.",
        ),
        (
            TextMatchQuestionRule(question_id="q2", answers=["yes"]),
            "Rule of type TEXT_MATCH is not compatible with question type CHOICE.",
        ),
    ],
)
def test_invalid_or_incompatible_candidate_is_not_executed(
    candidate: TextMatchQuestionRule,
    expected_error: str,
) -> None:
    result = execute_candidate_rule(
        candidate,
        _question_set(),
        [CandidateTestCase(case_id="case-1", answer_map={"q1": "yes"})],
    )

    assert result.validation.valid is False
    assert expected_error in result.validation.errors
    assert result.results_by_case_id == {}


def test_candidate_execution_returns_identity_free_results_by_case_and_question() -> None:
    candidate = TextMatchQuestionRule(question_id="q1", answers=["yes"])
    cases = [
        CandidateTestCase(case_id="positive", answer_map={"q1": "yes"}),
        CandidateTestCase(case_id="negative", answer_map={"q1": "no"}),
    ]

    result = execute_candidate_rule(candidate, _question_set(), cases)

    assert result.validation.valid is True
    assert result.validation.errors == []
    assert set(result.results_by_case_id) == {"positive", "negative"}
    assert set(result.results_by_case_id["positive"]) == {"q1"}
    assert result.results_by_case_id["positive"]["q1"].passed is True
    assert result.results_by_case_id["positive"]["q1"].points == 2.0
    assert result.results_by_case_id["negative"]["q1"].passed is False
    assert result.results_by_case_id["negative"]["q1"].points == 0.0
    assert "student_id" not in result.model_dump()


def test_candidate_execution_discards_prior_results_and_does_not_mutate_cases() -> None:
    prior_q1 = _existing_result()
    prior_q2 = _existing_result()
    case = CandidateTestCase(
        case_id="case-1",
        answer_map={"q1": "no", "q2": {"A"}},
        result_map={"q1": prior_q1, "q2": prior_q2},
    )
    original = case.model_copy(deep=True)

    result = execute_candidate_rule(
        TextMatchQuestionRule(question_id="q1", answers=["yes"]),
        _question_set(),
        [case],
    )

    actual = result.results_by_case_id["case-1"]
    assert set(actual) == {"q1"}
    assert actual["q1"].rule == "Text Match"
    assert actual["q1"].points == 0.0
    assert case == original


def test_candidate_execution_propagates_strict_missing_answer() -> None:
    # The case omits q1 entirely to verify that authoring-time execution fails loudly
    # instead of turning malformed test evidence into an ordinary zero-point result.
    with pytest.raises(GradingError) as exc_info:
        execute_candidate_rule(
            TextMatchQuestionRule(question_id="q1", answers=["yes"]),
            _question_set(),
            [CandidateTestCase(case_id="missing-answer", answer_map={"q2": {"A"}})],
        )

    assert exc_info.value.student_id == "missing-answer"
    assert exc_info.value.question_id == "q1"


def test_candidate_execution_propagates_strict_processing_error() -> None:
    # A parsed CHOICE answer must be a set. Supplying a string deliberately simulates
    # malformed internal data; TEXT_MATCH/LENGTH would stringify it and would not fail.
    with pytest.raises(GradingError) as exc_info:
        execute_candidate_rule(
            MultipleChoiceQuestionRule(question_id="q2", answer={"A"}),
            _question_set(),
            [CandidateTestCase(case_id="wrong-answer-type", answer_map={"q2": "A"})],
        )

    assert exc_info.value.student_id == "wrong-answer-type"
    assert exc_info.value.question_id == "q2"


def test_candidate_execution_rejects_duplicate_case_ids() -> None:
    with pytest.raises(ValueError, match="case IDs must be unique"):
        execute_candidate_rule(
            TextMatchQuestionRule(question_id="q1", answers=["yes"]),
            _question_set(),
            [
                CandidateTestCase(case_id="duplicate", answer_map={"q1": "yes"}),
                CandidateTestCase(case_id="duplicate", answer_map={"q1": "no"}),
            ],
        )
