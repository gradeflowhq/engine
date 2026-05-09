from __future__ import annotations

from collections.abc import Sequence
from functools import reduce
from operator import or_
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, Discriminator
from pydantic.json_schema import JsonDict

from ..questions.types import QuestionId, QuestionType
from .context import RuleContext, RulePath
from .models.base import BaseMultiQuestionRule, BaseRule, BaseSingleQuestionRule

GRADEFLOW_KEY = "x-gradeflow"
GRADEFLOW_INPUT_FIELD = "input"
GRADEFLOW_SUGGESTIONS_FIELD = "suggestions"
RULE_INPUT = "rule"
RULE_LIST_INPUT = "rule-list"
STRING_LIST_INPUT = "string-list"
CODE_INPUT = "code"


def gradeflow_schema_extra(
    input_type: str,
    *,
    suggestions: Sequence[str] | None = None,
) -> JsonDict:
    metadata: JsonDict = {GRADEFLOW_INPUT_FIELD: input_type}
    if suggestions:
        metadata[GRADEFLOW_SUGGESTIONS_FIELD] = list(suggestions)
    return {GRADEFLOW_KEY: metadata}


def rule_type(rule: type[BaseRule]) -> str:
    return cast(str, rule.model_fields["type"].default)


def rule_label(rule: type[BaseRule]) -> str:
    return cast(str, rule.model_fields["display_name"].default)


def rule_question_types(rule: type[BaseRule]) -> frozenset[QuestionType]:
    return cast(frozenset[QuestionType], rule.model_fields["question_types"].default)


def question_rule_classes() -> tuple[type[BaseRule], ...]:
    return _rule_subclasses(BaseSingleQuestionRule)


def global_rule_classes() -> tuple[type[BaseRule], ...]:
    return _rule_subclasses(BaseMultiQuestionRule)


def value_rule_classes() -> tuple[type[BaseRule], ...]:
    return tuple(
        rule
        for rule in _rule_subclasses(BaseRule)
        if not issubclass(rule, (BaseSingleQuestionRule, BaseMultiQuestionRule))
    )


def context_for_path(context: RuleContext, path: str | None) -> RuleContext:
    if not path:
        return context

    parsed_path = _parse_path(path)
    for rule in (*global_rule_classes(), *question_rule_classes()):
        nested_context = rule.nested_context(context, parsed_path)
        if nested_context is not None:
            return nested_context
    raise ValueError(f"Unknown rule path: {path}")


def compatible_rule_classes(context: RuleContext) -> tuple[type[BaseRule], ...]:
    if context.scope == "global":
        rules = global_rule_classes()
    elif context.scope == "question":
        rules = question_rule_classes()
    else:
        rules = value_rule_classes()

    if context.question_type is None:
        return rules
    return tuple(rule for rule in rules if context.question_type in rule_question_types(rule))


def rule_class(requested_type: str, context: RuleContext) -> type[BaseRule]:
    for rule in compatible_rule_classes(context):
        if rule_type(rule) == requested_type:
            return rule
    raise ValueError(f"Unknown rule type for this rule context: {requested_type}")


def question_rule_union(context: RuleContext) -> object:
    return _discriminated_union(
        [
            rule.from_context(context)
            for rule in question_rule_classes()
            if _compatible_question_ids(context, rule)
        ]
    )


def value_rule_union(question_type: QuestionType) -> object:
    return _discriminated_union(
        [rule for rule in value_rule_classes() if question_type in rule_question_types(rule)]
    )


def value_rule_union_for_question_types(question_types: Sequence[QuestionType]) -> object:
    compatible_question_types = frozenset(question_types)
    return _discriminated_union(
        [
            rule
            for rule in value_rule_classes()
            if compatible_question_types & rule_question_types(rule)
        ]
    )


def literal_type(values: Sequence[str]) -> object:
    return str if not values else Literal.__getitem__(tuple(values))


def _parse_path(path: str) -> RulePath:
    parts: list[str | int] = []
    for part in path.split("."):
        if not part:
            raise ValueError(f"Invalid rule path: {path}")
        parts.append(int(part) if part.isdecimal() else part)
    return tuple(parts)


def _discriminated_union(models: Sequence[type[BaseModel]]) -> object:
    if not models:
        raise ValueError("No compatible rules are available for this context")
    if len(models) == 1:
        return models[0]
    return Annotated[reduce(or_, models), Discriminator("type")]


def _rule_subclasses(rule: type[Any]) -> tuple[type[BaseRule], ...]:
    subclasses: list[type[BaseRule]] = []
    for subclass in rule.__subclasses__():
        typed_subclass = cast(type[BaseRule], subclass)
        subclasses.extend(_rule_subclasses(typed_subclass))
        if "type" in typed_subclass.model_fields:
            subclasses.append(typed_subclass)
    return tuple(subclasses)


def _compatible_question_ids(context: RuleContext, rule: type[BaseRule]) -> list[QuestionId]:
    return [
        question_id
        for question_id, question in context.question_set.question_map.items()
        if question.type in rule_question_types(rule)
    ]
