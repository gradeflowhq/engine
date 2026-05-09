import pytest
from pydantic import ValidationError

from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models import (
    ChoiceQuestion,
    MultiValuedQuestion,
    NumericQuestion,
    TextQuestion,
)
from gradeflow_engine.rules.context import RuleContext
from gradeflow_engine.rules.models.assumption_set import (
    Assumption,
    AssumptionSetMultiQuestionRule,
    MultiQuestionAssumption,
)
from gradeflow_engine.rules.models.base import BaseRule
from gradeflow_engine.rules.models.composite import CompositeQuestionRule
from gradeflow_engine.rules.models.conditional import ConditionalMultiQuestionRule
from gradeflow_engine.rules.models.keywords import KeywordsQuestionRule
from gradeflow_engine.rules.models.multi_valued import MultiValuedQuestionRule
from gradeflow_engine.rules.models.multiple_choice import MultipleChoiceQuestionRule
from gradeflow_engine.rules.models.number_equal import NumberEqualConfig, NumberEqualQuestionRule
from gradeflow_engine.rules.models.programmable import (
    ProgrammableMultiQuestionRule,
    ProgrammableQuestionRule,
    ProgrammableRule,
)
from gradeflow_engine.rules.models.programming import (
    ProgrammingConfig,
    ProgrammingRule,
    ProgrammingTestCase,
)
from gradeflow_engine.rules.models.regex import RegexConfig
from gradeflow_engine.rules.models.similarity import SimilarityQuestionRule
from gradeflow_engine.rules.models.text_match import TextMatchQuestionRule, TextMatchRule
from gradeflow_engine.rules.schema import (
    CODE_INPUT,
    GRADEFLOW_INPUT_FIELD,
    GRADEFLOW_KEY,
    GRADEFLOW_SUGGESTIONS_FIELD,
    STRING_LIST_INPUT,
    compatible_rule_classes,
    context_for_path,
    rule_type,
)
from gradeflow_engine.submissions.models import Submission


def test_rule_from_context_removes_internal_fields_and_applies_overrides() -> None:
    question = ChoiceQuestion(options={"A", "B"})
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    model = MultipleChoiceQuestionRule.from_context(context)

    assert "type" in model.model_fields
    assert "question_id" in model.model_fields
    assert "id" not in model.model_fields
    schema = model.model_json_schema()
    assert schema["properties"]["type"]["const"] == "MULTIPLE_CHOICE"
    assert schema["properties"]["type"]["default"] == "MULTIPLE_CHOICE"
    assert schema["properties"]["question_id"]["const"] == "q1"
    assert schema["properties"]["question_id"]["default"] == "q1"
    assert schema["properties"]["question_id"]["readOnly"] is True
    assert model(type="MULTIPLE_CHOICE", question_id="q1", answer={"A"}).model_dump()["answer"] == {
        "A"
    }
    with pytest.raises(ValidationError):
        model(question_id="q1", answer={"C"})


def test_rule_schema_titles_use_display_name_for_raw_and_contextual_models() -> None:
    question = TextQuestion()
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    assert ProgrammableQuestionRule.model_json_schema()["title"] == "Programmable"
    assert ProgrammableQuestionRule.from_context(context).model_json_schema()["title"] == (
        "Programmable"
    )


def test_rule_child_models_have_display_ready_schema_titles() -> None:
    assert Assumption.model_json_schema()["title"] == "Assumption"
    assert MultiQuestionAssumption.model_json_schema()["title"] == "Assumption"
    assert ProgrammingTestCase.model_json_schema()["title"] == "Test Case"
    assert ProgrammingConfig.model_json_schema()["title"] == "Programming Configuration"
    assert RegexConfig.model_json_schema()["title"] == "Regex Configuration"
    assert NumberEqualConfig.model_json_schema()["title"] == "Number Equal Configuration"

    programming_defs = ProgrammingRule.model_json_schema()["$defs"]
    assert programming_defs["ProgrammingTestCase"]["title"] == "Test Case"
    assert programming_defs["ProgrammingConfig"]["title"] == "Programming Configuration"

    parameter_defs = ProgrammableRule.model_json_schema()["$defs"]
    assert parameter_defs["IntParameter"]["title"] == "Integer"
    assert parameter_defs["FloatParameter"]["title"] == "Float"
    assert parameter_defs["StringParameter"]["title"] == "String"
    assert parameter_defs["BooleanParameter"]["title"] == "Boolean"
    assert parameter_defs["ListParameter"]["title"] == "List"
    assert parameter_defs["DictParameter"]["title"] == "Dictionary"


def test_initial_value_from_context_keeps_rule_defaults_needed_to_create_rule() -> None:
    question = ChoiceQuestion(options={"A", "B"})
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    initial = MultipleChoiceQuestionRule.initial_value_from_context(context)

    assert initial["type"] == "MULTIPLE_CHOICE"
    assert initial["scope"] == "question"
    assert initial["question_id"] == "q1"
    assert "id" not in initial


def test_rule_id_is_read_only_in_raw_rule_schemas() -> None:
    schema = TextMatchRule.model_json_schema()

    assert schema["properties"]["id"]["readOnly"] is True


def test_text_match_context_embeds_answer_suggestions() -> None:
    question = TextQuestion()
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        submissions=[
            Submission(student_id=f"s{i}", answer_map={"q1": f"answer {i}"}) for i in range(25)
        ],
        question_id="q1",
        question=question,
    )

    schema = TextMatchQuestionRule.from_context(context).model_json_schema()

    answers_schema = schema["properties"]["answers"]
    assert answers_schema[GRADEFLOW_KEY] == {
        GRADEFLOW_INPUT_FIELD: STRING_LIST_INPUT,
        GRADEFLOW_SUGGESTIONS_FIELD: [f"answer {i}" for i in range(25)],
    }
    assert "examples" not in answers_schema


def test_number_equal_context_uses_string_list_with_numeric_suggestions() -> None:
    question = NumericQuestion()
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        submissions=[
            Submission(student_id="s1", answer_map={"q1": 90}),
            Submission(student_id="s2", answer_map={"q1": 76.5}),
        ],
        question_id="q1",
        question=question,
    )

    schema = NumberEqualQuestionRule.from_context(context).model_json_schema()
    answers_schema = schema["properties"]["answers"]

    assert answers_schema["items"]["type"] == "string"
    assert answers_schema[GRADEFLOW_KEY] == {
        GRADEFLOW_INPUT_FIELD: STRING_LIST_INPUT,
        GRADEFLOW_SUGGESTIONS_FIELD: ["90", "76.5"],
    }
    assert "examples" not in answers_schema
    assert NumberEqualQuestionRule.model_validate(
        {"question_id": "q1", "answers": ["90", "76.5"]}
    ).answers == [90, 76.5]


def test_keywords_context_suggests_distinct_words_from_answers() -> None:
    question = TextQuestion()
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        submissions=[
            Submission(student_id="s1", answer_map={"q1": "buy house"}),
            Submission(student_id="s2", answer_map={"q1": "pay"}),
            Submission(student_id="s3", answer_map={"q1": "house"}),
            Submission(student_id="s4", answer_map={"q1": "AI, buy."}),
        ],
        question_id="q1",
        question=question,
    )

    keywords_schema = KeywordsQuestionRule.from_context(context).model_json_schema()["properties"][
        "keywords"
    ]

    assert keywords_schema[GRADEFLOW_KEY] == {
        GRADEFLOW_INPUT_FIELD: STRING_LIST_INPUT,
        GRADEFLOW_SUGGESTIONS_FIELD: ["buy", "house", "pay", "AI"],
    }
    assert "examples" not in keywords_schema


@pytest.mark.parametrize(
    ("rule", "field_name"),
    [
        (TextMatchQuestionRule, "answers"),
        (KeywordsQuestionRule, "keywords"),
        (SimilarityQuestionRule, "references"),
    ],
)
def test_string_list_context_fields_keep_input_hint_without_examples(
    rule: type[BaseRule],
    field_name: str,
) -> None:
    question = TextQuestion()
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    field_schema = rule.from_context(context).model_json_schema()["properties"][field_name]

    assert field_schema[GRADEFLOW_KEY] == {GRADEFLOW_INPUT_FIELD: STRING_LIST_INPUT}
    assert "examples" not in field_schema


def test_multi_valued_initial_value_has_one_slot_per_question_value() -> None:
    question = MultiValuedQuestion(value_types=["TEXT", "NUMERIC"])
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    initial = MultiValuedQuestionRule.initial_value_from_context(context)

    assert initial["rules"] == [{}, {}]


def test_multi_valued_context_schema_uses_fixed_length_array_items() -> None:
    question = MultiValuedQuestion(value_types=["TEXT", "NUMERIC"])
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    schema = MultiValuedQuestionRule.from_context(context).model_json_schema()
    rules_schema = schema["properties"]["rules"]

    assert rules_schema["minItems"] == 2
    assert rules_schema["maxItems"] == 2
    assert "items" in rules_schema
    assert "prefixItems" not in rules_schema


def test_assumption_set_initial_value_starts_with_empty_assumptions() -> None:
    context = RuleContext(
        scope="global",
        question_set=QuestionSet(question_map={"q1": TextQuestion()}),
    )

    initial = AssumptionSetMultiQuestionRule.initial_value_from_context(context)

    assert initial["assumptions"] == []


def test_programmable_multi_target_question_ids_use_string_list_input() -> None:
    context = RuleContext(
        scope="global",
        question_set=QuestionSet(question_map={"q1": TextQuestion(), "q2": ChoiceQuestion()}),
    )

    schema = ProgrammableMultiQuestionRule.from_context(context).model_json_schema()
    target_schema = schema["properties"]["target_question_ids"]

    assert target_schema[GRADEFLOW_KEY] == {GRADEFLOW_INPUT_FIELD: STRING_LIST_INPUT}
    assert "examples" not in target_schema
    assert target_schema["items"]["enum"] == ["q1", "q2"]


def test_code_fields_keep_code_input_hint_on_raw_schemas() -> None:
    assert ProgrammableRule.model_json_schema()["properties"]["code"][GRADEFLOW_KEY] == {
        GRADEFLOW_INPUT_FIELD: CODE_INPUT
    }

    config_schema = ProgrammingConfig.model_json_schema()["properties"]
    assert config_schema["prepend_code"][GRADEFLOW_KEY] == {GRADEFLOW_INPUT_FIELD: CODE_INPUT}
    assert config_schema["append_code"][GRADEFLOW_KEY] == {GRADEFLOW_INPUT_FIELD: CODE_INPUT}


def test_context_for_path_resolves_multi_value_slot() -> None:
    question = MultiValuedQuestion(value_types=["TEXT", "NUMERIC"])
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    nested = context_for_path(context, "rules.1")

    assert nested.scope == "value"
    assert nested.slot_index == 1
    assert nested.question_type == "NUMERIC"
    rule_types = {rule_type(rule) for rule in compatible_rule_classes(nested)}
    assert "NUMBER_EQUAL" in rule_types
    assert "KEYWORDS" not in rule_types


def test_context_for_path_resolves_nested_question_rule() -> None:
    context = RuleContext(
        scope="global",
        question_set=QuestionSet(question_map={"q1": TextQuestion()}),
    )

    nested = context_for_path(context, "then_rules.0")

    assert nested.scope == "question"
    assert nested.question_id is None
    rule_types = {rule_type(rule) for rule in compatible_rule_classes(nested)}
    assert "TEXT_MATCH" in rule_types
    assert "CONDITIONAL" not in rule_types


def test_context_for_path_preserves_selected_nested_question() -> None:
    question = TextQuestion()
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    nested = context_for_path(context, "then_rules.0")

    assert nested.scope == "question"
    assert nested.question_id == "q1"
    assert nested.question_id_editable is True
    assert nested.question_type == "TEXT"


def test_selected_nested_question_id_stays_editable() -> None:
    question = TextQuestion()
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    nested = context_for_path(context, "then_rules.0")
    schema = TextMatchQuestionRule.from_context(nested).model_json_schema()
    question_id_schema = schema["properties"]["question_id"]

    assert "const" not in question_id_schema
    assert "readOnly" not in question_id_schema
    assert question_id_schema["enum"] == ["q1"]
    assert "examples" not in question_id_schema


def test_context_for_path_resolves_assumption_children() -> None:
    question = TextQuestion()
    question_set = QuestionSet(question_map={"q1": question})
    question_context = RuleContext(
        scope="question",
        question_set=question_set,
        question_id="q1",
        question=question,
    )
    global_context = RuleContext(scope="global", question_set=question_set)

    assert context_for_path(question_context, "assumptions.0.rule").scope == "value"
    assert context_for_path(global_context, "assumptions.0.rules.0").scope == "question"


def test_value_rule_initial_value_does_not_include_question_id() -> None:
    question = TextQuestion()
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    nested = context_for_path(context, "rules.0")
    initial = TextMatchRule.initial_value_from_context(nested)

    assert nested.scope == "value"
    assert "question_id" not in initial


def test_context_for_path_rejects_unknown_or_invalid_path() -> None:
    question = MultiValuedQuestion(value_types=["TEXT"])
    context = RuleContext(
        scope="question",
        question_set=QuestionSet(question_map={"q1": question}),
        question_id="q1",
        question=question,
    )

    with pytest.raises(ValueError, match="Value slot 1 does not exist"):
        context_for_path(context, "rules.1")

    with pytest.raises(ValueError, match="Unknown rule path"):
        context_for_path(context, "missing.0")


def test_context_for_path_uses_rule_owned_path_semantics() -> None:
    assert ConditionalMultiQuestionRule.nested_context(
        RuleContext(scope="global", question_set=QuestionSet(question_map={})),
        ("if_rules", 0),
    )
    assert CompositeQuestionRule.nested_context(
        RuleContext(
            scope="question",
            question_set=QuestionSet(question_map={"q1": TextQuestion()}),
            question_id="q1",
            question=TextQuestion(),
        ),
        ("rules", 0),
    )
    assert not NumberEqualQuestionRule.nested_context(
        RuleContext(scope="global", question_set=QuestionSet(question_map={})),
        ("rules", 0),
    )
