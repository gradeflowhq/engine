from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeGuard

from ..questions.types import (
    Answer,
    ChoiceAnswer,
    MultiValuedAnswer,
    NumericAnswer,
    QuestionId,
    QuestionType,
    SingleValuedAnswer,
    TextAnswer,
)
from .types import RuleValidationError

if TYPE_CHECKING:
    from ..rules.models import QuestionRule


def is_text(a: Any) -> TypeGuard[TextAnswer]:
    return isinstance(a, str) or is_numeric(a)


def is_numeric(a: Any) -> TypeGuard[NumericAnswer]:
    # Exclude bool (bool is a subclass of int)
    return isinstance(a, (int, float)) and not isinstance(a, bool)


def is_single_valued(a: Any) -> TypeGuard[SingleValuedAnswer]:
    return is_text(a) or is_numeric(a)


def is_choice(a: Any) -> TypeGuard[ChoiceAnswer]:
    return isinstance(a, set) and all(isinstance(x, str) for x in a)  # type: ignore


def is_multi_valued(a: Any) -> TypeGuard[MultiValuedAnswer]:
    return isinstance(a, list) and all(is_single_valued(x) for x in a)  # type: ignore


Validator = Callable[[Any], bool]
validators: dict[QuestionType, Validator] = {
    "TEXT": is_text,
    "NUMERIC": is_numeric,
    "CHOICE": is_choice,
    "MULTI_VALUED": is_multi_valued,
}


def validate_answer_type(answer: Answer, question_types: frozenset[QuestionType]) -> Answer:
    for qt in question_types:
        validator = validators.get(qt)
        if validator is None:
            raise ValueError(f"Unknown question type: {qt}")
        if validator(answer):
            return answer
    raise TypeError(
        f"Answer type {type(answer).__name__} is not compatible with rule types "
        f"{list(question_types)}"
    )


def validate_unique_target_questions_in_rules(
    rules: list["QuestionRule"],
) -> list[RuleValidationError]:
    # Aggregate errors from individual rule validations
    errors: list[RuleValidationError] = []
    for rule in rules:
        errors.extend(rule.validate_unique_target_questions())

    # Build a mapping from question IDs to the rules that target them
    rule_map: dict[QuestionId, list["QuestionRule"]] = {}
    for rule in rules:
        target_question_ids = rule.get_target_question_ids()
        for qid in target_question_ids:
            if qid not in rule_map:
                rule_map[qid] = []
            rule_map[qid].append(rule)

    # Check for duplicate targeting
    for qid, rules in rule_map.items():
        if len(rules) > 1:
            rule_types = [rule.type for rule in rules]
            errors.append(f"Question ID {qid} is targeted by multiple rules: {rule_types}")
    return errors
