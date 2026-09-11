"""Provider-neutral rule authoring and candidate execution APIs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .exceptions import UnknownQuestionError
from .question_sets.model import QuestionSet
from .questions.types import Answer, QuestionId, QuestionType
from .rubrics.model import Rubric
from .rules.context import RuleContext
from .rules.models import QuestionRule
from .rules.result import QuestionResult
from .rules.schema import (
    compatible_rule_classes,
    rule_label,
    rule_type,
)
from .rules.types import RuleValidationError
from .submissions.models import Submission

__all__ = [
    "CandidateExecutionResult",
    "CandidateTestCase",
    "CandidateValidationResult",
    "QuestionRuleCatalog",
    "QuestionRuleCatalogEntry",
    "execute_candidate_rule",
    "get_question_rule_catalog",
    "validate_candidate_rule",
]

CaseId = str


class QuestionRuleCatalogEntry(BaseModel):
    """One rule type that is compatible with a selected question."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    type: str
    display_name: str
    json_schema: dict[str, Any]
    initial_value: dict[str, Any]


class QuestionRuleCatalog(BaseModel):
    """Contextual rule authoring metadata for a selected question."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    question_id: QuestionId
    question_type: QuestionType
    rules: list[QuestionRuleCatalogEntry]


class CandidateTestCase(BaseModel):
    """An identity-free answer case used to exercise a candidate rule."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    case_id: CaseId = Field(min_length=1)
    answer_map: dict[QuestionId, Answer]
    result_map: dict[QuestionId, QuestionResult] = Field(default_factory=dict)


class CandidateValidationResult(BaseModel):
    """Full-rubric validation outcome for a candidate rule."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    valid: bool
    errors: list[RuleValidationError]


class CandidateExecutionResult(BaseModel):
    """Validation and deterministic results from candidate test execution."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    validation: CandidateValidationResult
    results_by_case_id: dict[CaseId, dict[QuestionId, QuestionResult]]


def get_question_rule_catalog(
    question_set: QuestionSet,
    question_id: QuestionId,
    *,
    submissions: Sequence[Submission] = (),
) -> QuestionRuleCatalog:
    """Return compatible contextual schemas and initial values for a question."""
    question = question_set.question_map.get(question_id)
    if question is None:
        raise UnknownQuestionError(question_id)

    context = RuleContext(
        scope="question",
        question_set=question_set,
        submissions=submissions,
        question_id=question_id,
        question=question,
    )
    entries = [
        QuestionRuleCatalogEntry(
            type=rule_type(rule),
            display_name=rule_label(rule),
            json_schema=rule.from_context(context).model_json_schema(mode="validation"),
            initial_value=rule.initial_value_from_context(context),
        )
        for rule in compatible_rule_classes(context)
    ]
    entries.sort(key=lambda entry: entry.type)
    return QuestionRuleCatalog(
        question_id=question_id,
        question_type=question.type,
        rules=entries,
    )


def validate_candidate_rule(
    candidate: QuestionRule,
    question_set: QuestionSet,
    *,
    base_rubric: Rubric | None = None,
) -> CandidateValidationResult:
    """Validate a candidate as part of the complete prospective rubric."""
    existing_rules = [] if base_rubric is None else list(base_rubric.rules)
    errors = Rubric(rules=[*existing_rules, candidate]).validate_rubric(question_set)
    return CandidateValidationResult(valid=not errors, errors=errors)


def execute_candidate_rule(
    candidate: QuestionRule,
    question_set: QuestionSet,
    cases: Sequence[CandidateTestCase],
    *,
    base_rubric: Rubric | None = None,
) -> CandidateExecutionResult:
    """Validate and strictly execute a candidate without retaining prior results."""
    validation = validate_candidate_rule(
        candidate,
        question_set,
        base_rubric=base_rubric,
    )
    if not validation.valid:
        return CandidateExecutionResult(validation=validation, results_by_case_id={})

    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Candidate test case IDs must be unique")

    test_submissions = [
        Submission(
            student_id=case.case_id,
            answer_map=dict(case.answer_map),
            result_map={},
        )
        for case in cases
    ]
    graded = Rubric(rules=[candidate]).grade(
        test_submissions,
        question_set.question_map,
        strict=True,
        override_results=True,
        grade_questions_without_rule=False,
        parallel_jobs=1,
    )
    return CandidateExecutionResult(
        validation=validation,
        results_by_case_id={
            submission.student_id: dict(submission.result_map) for submission in graded
        },
    )
