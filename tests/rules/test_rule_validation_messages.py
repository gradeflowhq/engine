import pytest
from pydantic import TypeAdapter, ValidationError

from gradeflow_engine.error_formatting import format_validation_error_details
from gradeflow_engine.exceptions import RubricValidationError
from gradeflow_engine.rubrics.model import Rubric
from gradeflow_engine.rules.models import QuestionRule

QUESTION_RULE_ADAPTER: TypeAdapter[object] = TypeAdapter(QuestionRule)

RAW_PYDANTIC_FRAGMENTS = (
    "Input should be",
    "validation error for",
    "Unable to extract tag",
    "For further information",
    "type=",
)


def _validate_rubric(data: object) -> None:
    try:
        Rubric.model_validate(data)
    except ValidationError as e:
        raise RubricValidationError(e) from e


def _question_rule_messages(data: object) -> list[str]:
    with pytest.raises(ValidationError) as exc_info:
        QUESTION_RULE_ADAPTER.validate_python(data)
    return format_validation_error_details(exc_info.value.errors())


INVALID_RULE_CASES = [
    (
        "ASSUMPTION_SET",
        {
            "type": "ASSUMPTION_SET",
            "question_id": "q1",
            "assumptions": [{"weight": "bad", "rule": {"type": "LENGTH", "min_length": 1}}],
        },
        "Rule 1 > Assumption Set > Assumption 1 > weight must be a number.",
    ),
    (
        "ASSUMPTION_SET_MULTI",
        {
            "type": "ASSUMPTION_SET_MULTI",
            "assumptions": [
                {"rules": [{"type": "LENGTH", "question_id": "q1", "min_length": "bad"}]}
            ],
        },
        (
            "Rule 1 > Assumption Set Multi > Assumption 1 > "
            "Rule 1 > Length > min length must be a whole number."
        ),
    ),
    (
        "BONUS",
        {"type": "BONUS", "question_id": 123},
        "Rule 1 > Bonus > question id must be text.",
    ),
    (
        "CODE_TESTS",
        {"type": "CODE_TESTS", "question_id": "q1", "testcases": []},
        "Rule 1 > Code Tests > testcases must contain at least 1 items.",
    ),
    (
        "COMPOSITE",
        {
            "type": "COMPOSITE",
            "question_id": "q1",
            "rules": [{"type": "LENGTH", "min_length": "bad"}],
        },
        "Rule 1 > Composite > Rule 1 > Length > min length must be a whole number.",
    ),
    (
        "CONDITIONAL",
        {"type": "CONDITIONAL", "if_rules": [], "then_rules": [], "else_rules": []},
        "Rule 1 > Conditional > if rules must contain at least 1 items.",
    ),
    (
        "CUSTOM_CODE",
        {"type": "CUSTOM_CODE", "question_id": "q1", "parameters": {"p": {"dtype": "Bad"}}},
        "Rule 1 > Custom Code > parameters > p has an unknown type 'Bad'.",
    ),
    (
        "CUSTOM_CODE_MULTI",
        {"type": "CUSTOM_CODE_MULTI", "target_question_ids": [], "parameters": {}},
        "Rule 1 > Custom Code Multi > target question ids must contain at least 1 items.",
    ),
    (
        "KEYWORDS",
        {"type": "KEYWORDS", "question_id": "q1", "keywords": []},
        "Rule 1 > Keywords > keywords must contain at least 1 items.",
    ),
    (
        "LENGTH",
        {"type": "LENGTH", "question_id": "q1", "min_length": "bad"},
        "Rule 1 > Length > min length must be a whole number.",
    ),
    (
        "MULTIPLE_CHOICE",
        {"type": "MULTIPLE_CHOICE", "question_id": "q1", "answer": []},
        "Rule 1 > Multiple Choice > answer must contain at least 1 items.",
    ),
    (
        "MULTI_VALUED",
        {"type": "MULTI_VALUED", "question_id": "q1", "rules": []},
        "Rule 1 > Multi Valued > rules must contain at least 1 items.",
    ),
    (
        "NUMBER_EQUAL",
        {"type": "NUMBER_EQUAL", "question_id": "q1", "answers": []},
        "Rule 1 > Number Equal > answers must contain at least 1 items.",
    ),
    (
        "NUMERIC_RANGE",
        {"type": "NUMERIC_RANGE", "question_id": "q1", "min_value": "bad"},
        "Rule 1 > Numeric Range > min value must be a number.",
    ),
    (
        "REGEX",
        {"type": "REGEX", "question_id": "q1"},
        "Rule 1 > Regex > pattern is required.",
    ),
    (
        "SIMILARITY",
        {"type": "SIMILARITY", "question_id": "q1", "references": ["yes"], "threshold": "bad"},
        "Rule 1 > Similarity > threshold must be a number.",
    ),
    (
        "TEXT_MATCH",
        {"type": "TEXT_MATCH", "question_id": "q1", "answers": []},
        "Rule 1 > Text Match > answers must contain at least 1 items.",
    ),
]


@pytest.mark.parametrize(
    ("rule_type", "payload", "expected_detail"),
    INVALID_RULE_CASES,
    ids=[case[0] for case in INVALID_RULE_CASES],
)
def test_rule_validation_errors_are_user_friendly(
    rule_type: str,
    payload: dict[str, object],
    expected_detail: str,
) -> None:
    with pytest.raises(RubricValidationError) as exc_info:
        _validate_rubric({"rules": [payload]})

    assert rule_type in str(payload["type"])
    assert expected_detail in str(exc_info.value)
    assert not any(fragment in str(exc_info.value) for fragment in RAW_PYDANTIC_FRAGMENTS)


def test_rule_validation_details_are_user_friendly() -> None:
    messages = _question_rule_messages({"type": "LENGTH", "question_id": "q1", "min_length": "bad"})

    assert messages == ["Length > min length must be a whole number."]
    assert not any(fragment in str(messages) for fragment in RAW_PYDANTIC_FRAGMENTS)


def test_assumption_rule_item_locations_are_named() -> None:
    messages = _question_rule_messages(
        {
            "type": "ASSUMPTION_SET",
            "question_id": "q1",
            "assumptions": [{"weight": 1, "rule": {"type": "MULTIPLE_CHOICE", "answer": [1]}}],
        }
    )

    assert messages == [
        "Assumption Set > Assumption 1 > rule > Multiple Choice > Answer 1 must be text."
    ]


def test_nested_rule_object_type_errors_are_user_friendly() -> None:
    messages = _question_rule_messages(
        {
            "type": "ASSUMPTION_SET",
            "question_id": "q1",
            "assumptions": [{"weight": 1, "rule": "bad"}],
        }
    )

    assert messages == ["Assumption Set > Assumption 1 > rule must be an object."]


@pytest.mark.parametrize("blank_rule", [None, "", {}, {"type": ""}, {"type": None}])
def test_blank_nested_rule_slots_prompt_rule_selection(blank_rule: object) -> None:
    messages = _question_rule_messages(
        {
            "type": "MULTI_VALUED",
            "question_id": "q1",
            "rules": [blank_rule],
        }
    )

    assert messages == ["Please select a valid rule for Multi Valued > Rule 1."]


def test_numeric_union_branch_errors_are_collapsed() -> None:
    payload = {
        "type": "COMPOSITE",
        "question_id": "q1",
        "rules": [{"type": "NUMBER_EQUAL", "answers": ["bad"]}],
    }

    messages = _question_rule_messages(payload)

    assert messages == ["Composite > Rule 1 > Number Equal > Answer 1 must be a number."]

    with pytest.raises(RubricValidationError) as rubric_exc_info:
        _validate_rubric({"rules": [payload]})

    assert rubric_exc_info.value.messages == [
        "Rule 1 > Composite > Rule 1 > Number Equal > Answer 1 must be a number."
    ]


def test_uppercase_mapping_keys_are_not_treated_as_type_tags() -> None:
    messages = _question_rule_messages(
        {
            "type": "CUSTOM_CODE",
            "question_id": "q1",
            "parameters": {"MY_PARAM": {"dtype": "Int", "value": "bad"}},
        }
    )

    assert messages == ["Custom Code > parameters > MY PARAM > Int > value must be a whole number."]


def test_nested_question_rule_locations_use_rule_labels() -> None:
    messages = _question_rule_messages(
        {
            "type": "ASSUMPTION_SET_MULTI",
            "assumptions": [
                {
                    "rules": [
                        {"type": "BONUS"},
                        {"type": "ASSUMPTION_SET", "assumptions": []},
                    ]
                }
            ],
        }
    )

    assert messages == [
        "Assumption Set Multi > Assumption 1 > Rule 1 > Bonus > question id is required.",
        (
            "Assumption Set Multi > Assumption 1 > Rule 2 > "
            "Assumption Set > question id is required."
        ),
    ]


def test_collection_item_locations_are_generic() -> None:
    messages = _question_rule_messages(
        {"type": "CODE_TESTS", "question_id": "q1", "testcases": [{}]}
    )

    assert messages == [
        "Code Tests > Testcase 1 > expression is required.",
        "Code Tests > Testcase 1 > expected is required.",
    ]
