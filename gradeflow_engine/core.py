from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, Field

from .question_sets.inference import (
    DEFAULT_CHOICE_DELIMITER,
    DEFAULT_CHOICE_NORMALIZE_CASE,
    DEFAULT_CHOICE_OPTION_LIMIT,
    DEFAULT_EMPTY_MARKER,
    DEFAULT_MULTI_VALUE_DELIMITER,
)
from .question_sets.loaders import BaseQuestionSetLoader
from .question_sets.model import QuestionSet
from .question_sets.savers import BaseQuestionSetSaver
from .question_sets.savers.base import QuestionSetSaverOutput
from .registry import (
    question_set_loader_registry,
    question_set_saver_registry,
    rubric_loader_registry,
    submissions_loader_registry,
    submissions_saver_registry,
)
from .rubrics.loaders import BaseRubricLoader
from .rubrics.model import Rubric, RubricCoverage
from .rules.types import RuleValidationError
from .submissions.loaders import BaseSubmissionsLoader
from .submissions.models import GradedSubmission, RawSubmission, Submission
from .submissions.savers import BaseSubmissionsSaver
from .submissions.savers.base import SubmissionsSaverOutput

# ---------------------------
# Registry discovery helpers
# ---------------------------


def list_available_question_set_loaders() -> list[str]:
    return question_set_loader_registry.available()


def list_available_question_set_savers() -> list[str]:
    return question_set_saver_registry.available()


def list_available_rubric_loaders() -> list[str]:
    return rubric_loader_registry.available()


def list_available_submissions_loaders() -> list[str]:
    return submissions_loader_registry.available()


def list_available_submissions_savers() -> list[str]:
    return submissions_saver_registry.available()


# ---------------------------
# Registry getters
# ---------------------------


def get_question_set_loader_class(name: str) -> type[BaseQuestionSetLoader]:
    return question_set_loader_registry.get(name)


def get_question_set_saver_class(name: str) -> type[BaseQuestionSetSaver]:
    return question_set_saver_registry.get(name)


def get_rubric_loader_class(name: str) -> type[BaseRubricLoader]:
    return rubric_loader_registry.get(name)


def get_submissions_loader_class(name: str) -> type[BaseSubmissionsLoader]:
    return submissions_loader_registry.get(name)


def get_submissions_saver_class(name: str) -> type[BaseSubmissionsSaver]:
    return submissions_saver_registry.get(name)


# ---------------------------
# Load/save APIs
# ---------------------------


def load_question_set(
    data: str,
    *,
    loader_name: str = "YAML",
) -> QuestionSet:
    loader_cls = get_question_set_loader_class(loader_name)
    loader = loader_cls()
    return loader.load(data)


def save_question_set(
    question_set: QuestionSet,
    *,
    saver_name: str = "YAML",
) -> QuestionSetSaverOutput:
    saver_cls = get_question_set_saver_class(saver_name)
    saver = saver_cls()
    return saver.save(question_set)


def load_rubric(
    data: str,
    *,
    loader_name: str = "YAML",
) -> Rubric:
    loader_cls = get_rubric_loader_class(loader_name)
    loader = loader_cls()
    return loader.load(data)


def load_submissions(
    data: str,
    *,
    loader_name: str = "CSV",
    **loader_kwargs: object,
) -> list[RawSubmission]:
    """
    Load RawSubmission objects via the registered SubmissionsLoader.
    Arbitrary keyword arguments are validated by the loader's Pydantic model.
    Example kwargs for CSV loader: student_id_column="student_id", answer_columns=[...]
    """
    loader_cls = get_submissions_loader_class(loader_name)
    # Validate and construct the loader with provided kwargs
    loader = loader_cls.model_validate(loader_kwargs or {})
    return loader.load(data)


def save_graded_submissions(
    graded_submissions: Iterable[GradedSubmission],
    *,
    saver_name: str = "CSV",
    **saver_kwargs: object,
) -> SubmissionsSaverOutput:
    """
    Save graded submissions via the registered SubmissionsSaver.
    Arbitrary keyword arguments are validated by the saver’s Pydantic model.
    Example kwargs for CSV saver: student_id_column="student_id", include_answers=True, ...
    """
    saver_cls = get_submissions_saver_class(saver_name)
    # Validate and construct the saver with provided kwargs
    saver = saver_cls.model_validate(saver_kwargs or {})
    return saver.save(graded_submissions)


# ---------------------------
# Inference
# ---------------------------


def infer_question_set(
    raw_submissions: list[RawSubmission],
    *,
    choice_delimiter: str = DEFAULT_CHOICE_DELIMITER,
    choice_option_limit: int = DEFAULT_CHOICE_OPTION_LIMIT,
    choice_normalize_case: bool = DEFAULT_CHOICE_NORMALIZE_CASE,
    multi_value_delimiter: str = DEFAULT_MULTI_VALUE_DELIMITER,
    empty_marker: str = DEFAULT_EMPTY_MARKER,
) -> QuestionSet:
    return QuestionSet.infer(
        raw_submissions,
        choice_delimiter=choice_delimiter,
        choice_option_limit=choice_option_limit,
        choice_normalize_case=choice_normalize_case,
        multi_value_delimiter=multi_value_delimiter,
        empty_marker=empty_marker,
    )


# ---------------------------
# Coverage
# ---------------------------


def compute_rubric_coverage(
    rubric: Rubric,
    question_set: QuestionSet,
) -> RubricCoverage:
    return rubric.get_coverage(question_set)


# ---------------------------
# Pipeline
# ---------------------------


class PipelineResult(BaseModel):
    raw_submissions: list[RawSubmission]
    question_set: QuestionSet
    submissions: list[Submission]
    rubric: Rubric | None = None
    validation_errors: list[RuleValidationError] = Field(default_factory=list[RuleValidationError])
    graded_submissions: list[GradedSubmission] = Field(default_factory=list[GradedSubmission])
    output: SubmissionsSaverOutput | None = None
    coverage: RubricCoverage | None = None


def run_pipeline(
    *,
    # Submissions source (choose one; raw_submissions preferred if both provided):
    raw_submissions: list[RawSubmission] | None = None,
    submissions_data: str | None = None,
    submissions_loader_name: str = "CSV",
    submissions_loader_kwargs: dict[str, object] | None = None,
    submissions_parser_strict: bool = False,
    # Question set source (choose one; question_set preferred if both provided):
    question_set: QuestionSet | None = None,
    question_set_data: str | None = None,
    question_set_loader_name: str = "YAML",
    # Inference defaults (used only if question_set is not supplied in either form):
    choice_delimiter: str = DEFAULT_CHOICE_DELIMITER,
    choice_option_limit: int = DEFAULT_CHOICE_OPTION_LIMIT,
    multi_value_delimiter: str = DEFAULT_MULTI_VALUE_DELIMITER,
    # Rubric source (choose one; rubric preferred if both provided):
    rubric: Rubric | None = None,
    rubric_data: str | None = None,
    rubric_loader_name: str = "YAML",
    rubric_grading_strict: bool = False,
    # Optional saver (only used if we have a rubric and grading occurs):
    saver_name: str | None = "CSV",
    submissions_saver_kwargs: dict[str, object] | None = None,
) -> PipelineResult:
    """
    End-to-end pipeline with explicit source control.
    - submissions_loader_kwargs and submissions_saver_kwargs are passed to the respective
      Pydantic models via model_validate for configuration.
    """
    # Validate mutually exclusive question set inputs
    if question_set is not None and question_set_data is not None:
        raise ValueError("Provide either question_set or question_set_data, not both.")

    # Validate mutually exclusive rubric inputs
    if rubric is not None and rubric_data is not None:
        raise ValueError("Provide either rubric or rubric_data, not both.")

    # Resolve submissions
    if raw_submissions is not None:
        raw_subs = raw_submissions
    elif submissions_data is not None:
        raw_subs = load_submissions(
            submissions_data,
            loader_name=submissions_loader_name,
            **(submissions_loader_kwargs or {}),
        )
    else:
        raise ValueError(
            "Submissions source is required: provide raw_submissions or submissions_data."
        )

    # Resolve question set
    if question_set is not None:
        qset = question_set
    elif question_set_data is not None:
        qset = load_question_set(question_set_data, loader_name=question_set_loader_name)
    else:
        qset = infer_question_set(
            raw_subs,
            choice_delimiter=choice_delimiter,
            choice_option_limit=choice_option_limit,
            multi_value_delimiter=multi_value_delimiter,
        )

    # Parse submissions
    submissions = qset.parse(raw_subs, strict=submissions_parser_strict)

    # Resolve rubric, validate, and grade
    used_rubric: Rubric | None = None
    validation_errors: list[RuleValidationError] = []
    graded_submissions: list[GradedSubmission] = []
    coverage: RubricCoverage | None = None

    if rubric is not None:
        used_rubric = rubric
    elif rubric_data is not None:
        used_rubric = load_rubric(rubric_data, loader_name=rubric_loader_name)

    if used_rubric is not None:
        validation_errors = used_rubric.validate_rubric(qset)
        graded_submissions = used_rubric.grade(submissions, strict=rubric_grading_strict)
        coverage = compute_rubric_coverage(used_rubric, qset)

    # Optional save
    output: SubmissionsSaverOutput | None = None
    if saver_name is not None and graded_submissions:
        output = save_graded_submissions(
            graded_submissions,
            saver_name=saver_name,
            **(submissions_saver_kwargs or {}),
        )

    return PipelineResult(
        raw_submissions=raw_subs,
        question_set=qset,
        submissions=submissions,
        rubric=used_rubric,
        validation_errors=validation_errors,
        graded_submissions=graded_submissions,
        output=output,
        coverage=coverage,
    )


__all__ = [
    # Discovery
    "list_available_question_set_loaders",
    "list_available_question_set_savers",
    "list_available_rubric_loaders",
    "list_available_submissions_loaders",
    "list_available_submissions_savers",
    # Getters
    "get_question_set_loader_class",
    "get_question_set_saver_class",
    "get_rubric_loader_class",
    "get_submissions_loader_class",
    "get_submissions_saver_class",
    # Loading/saving
    "load_question_set",
    "save_question_set",
    "load_rubric",
    "load_submissions",
    "save_graded_submissions",
    # Inference & pipeline
    "infer_question_set",
    "PipelineResult",
    "run_pipeline",
    # Coverage
    "compute_rubric_coverage",
]
