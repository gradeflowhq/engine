import pytest

from gradeflow_engine.rules.markdown import markdown_code, markdown_join
from gradeflow_engine.rules.models import (
    Assumption,
    AssumptionSetMultiQuestionRule,
    AssumptionSetQuestionRule,
    BonusRule,
    CompositeRule,
    ConditionalMultiQuestionRule,
    CustomCodeMultiQuestionRule,
    CustomCodeRule,
    KeywordsRule,
    LengthRule,
    MultipleChoiceRule,
    MultiQuestionAssumption,
    MultiValuedRule,
    NumberEqualRule,
    NumericRangeRule,
    RegexRule,
    SimilarityRule,
    TextMatchQuestionRule,
    TextMatchRule,
)
from gradeflow_engine.rules.models.base import BaseRule
from gradeflow_engine.rules.models.code_tests import CodeTestCase, CodeTestRule


def test_markdown_code_handles_backticks() -> None:
    assert markdown_code("plain") == "`plain`"
    assert markdown_code("uses `backticks`") == "`` uses `backticks` ``"


def test_markdown_join_uses_requested_conjunction() -> None:
    assert markdown_join(["a"], conjunction="and") == "`a`"
    assert markdown_join(["a", "b"], conjunction="and") == "`a` and `b`"
    assert markdown_join(["a", "b"], conjunction="or") == "`a` or `b`"
    assert markdown_join(["a", "b", "c"], conjunction="and") == "`a`, `b`, and `c`"
    assert markdown_join(["a", "b", "c"], conjunction="or") == "`a`, `b`, or `c`"


@pytest.mark.parametrize(
    ("rule", "snippets"),
    [
        (BonusRule(), ["**Bonus:**"]),
        (TextMatchRule(answers=["Paris", "Lyon"]), ["`Paris`", "`Lyon`"]),
        (KeywordsRule(keywords=["alpha", "beta"]), ["`alpha`", "`beta`"]),
        (RegexRule(pattern=r"\d+"), [r"`\d+`"]),
        (NumberEqualRule(answers=[1, 2]), ["`1`", "`2`", "`1e-06`"]),
        (NumericRangeRule(min_value=1, max_value=2), ["`1.0`", "`2.0`"]),
        (LengthRule(min_length=1, max_length=5), ["`1`", "`5`"]),
        (MultipleChoiceRule(answer={"A", "B"}), ["`A`", "`B`"]),
        (
            SimilarityRule(references=["foo", "bar"], threshold=0.75, algorithm="jaro_winkler"),
            [
                "Accept answers at least `75%` similar to `foo` or `bar` using Jaro Winkler.",
            ],
        ),
        (
            CodeTestRule(testcases=[CodeTestCase(expression="add(1, 2)", expected="3")]),
            ["**Code must pass:**", "`add(1, 2)`", "`3`"],
        ),
        (CustomCodeRule(mode="PASS_FAIL"), ["`passed`"]),
        (
            CustomCodeMultiQuestionRule(
                target_question_ids=["Q1", "Q2"], code="results = {}", mode="PASS_FAIL"
            ),
            ["`Q1`", "`Q2`", "`passed`"],
        ),
        (
            CompositeRule(rules=[TextMatchRule(answers=["yes"])]),
            ["**All must be true** (`ALL`):", "`yes`"],
        ),
        (
            MultiValuedRule(rules=[TextMatchRule(answers=["yes"]), NumberEqualRule(answers=[1])]),
            ["**Value 1:**", "**Value 2:**", "`yes`", "`1`"],
        ),
        (
            ConditionalMultiQuestionRule(
                if_rules=[TextMatchQuestionRule(question_id="Q1", answers=["yes"])],
                then_rules=[TextMatchQuestionRule(question_id="Q2", answers=["ok"])],
                else_rules=[TextMatchQuestionRule(question_id="Q3", answers=["no"])],
            ),
            ["**IF** `Q1`:", "**THEN** `Q2`:", "**ELSE** `Q3`:"],
        ),
        (
            AssumptionSetQuestionRule(
                question_id="Q1",
                assumptions=[Assumption(name="Main", rule=TextMatchRule(answers=["yes"]))],
                mode="MAX",
            ),
            ["**Assumption 1 (`Main`):**", "`yes`"],
        ),
        (
            AssumptionSetMultiQuestionRule(
                assumptions=[
                    MultiQuestionAssumption(
                        name="Main",
                        rules=[TextMatchQuestionRule(question_id="Q1", answers=["yes"])],
                    )
                ],
                mode="MAX",
            ),
            ["**Assumption 1 (`Main`):**", "`Q1`:", "`yes`"],
        ),
    ],
)
def test_rule_descriptions_use_markdown(rule: BaseRule, snippets: list[str]) -> None:
    description = rule.description
    assert isinstance(description, str)
    for snippet in snippets:
        assert snippet in description


@pytest.mark.parametrize(
    ("rule", "snippet"),
    [
        (
            TextMatchRule(answers=["Paris", "Lyon"]),
            "Match one of these answers: `Paris` or `Lyon`.",
        ),
        (
            NumberEqualRule(answers=[1, 2]),
            "Approximately equal to: `1` or `2` within a tolerance of `1e-06`.",
        ),
        (
            KeywordsRule(keywords=["alpha", "beta"], mode="ALL"),
            "Contain all of these keywords: `alpha` and `beta`.",
        ),
        (
            KeywordsRule(keywords=["alpha", "beta"], mode="ANY"),
            "Contain at least one of these keywords: `alpha` or `beta`.",
        ),
        (
            MultipleChoiceRule(answer={"A", "B"}, mode="ALL"),
            "Include all of these choices: `A` and `B`.",
        ),
        (
            MultipleChoiceRule(answer={"A", "B"}, mode="ANY"),
            "Include at least one of these choices: `A` or `B`.",
        ),
        (
            MultipleChoiceRule(answer={"A", "B"}, mode="NOT_CONTAIN"),
            "Do not include any of these choices: `A` or `B`.",
        ),
        (
            SimilarityRule(references=["foo", "bar"], threshold=0.75, algorithm="jaro_winkler"),
            "Accept answers at least `75%` similar to `foo` or `bar` using Jaro Winkler.",
        ),
        (
            CustomCodeMultiQuestionRule(
                target_question_ids=["Q1", "Q2"], code="results = {}", mode="PASS_FAIL"
            ),
            "Custom multi-question code targeting `Q1` and `Q2`",
        ),
    ],
)
def test_rule_descriptions_use_semantic_list_conjunctions(rule: BaseRule, snippet: str) -> None:
    assert snippet in rule.description
