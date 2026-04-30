from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field

# Adapters (registries)
from .adapters.registries import (
    QuestionSetAdapter,
    RawSubmissionsAdapter,
    RubricAdapter,
    question_set_adapter_registry,
    raw_submissions_adapter_registry,
    rubric_adapter_registry,
)
from .exceptions import ConfigurationError
from .io.sinks import DataSink

# IO abstractions
from .io.sources import DataSource

# Domain models and inference defaults
from .question_sets.inference import (
    DEFAULT_CHOICE_DELIMITER,
    DEFAULT_CHOICE_NORMALIZE_CASE,
    DEFAULT_CHOICE_OPTION_LIMIT,
    DEFAULT_EMPTY_MARKER,
    DEFAULT_MULTI_VALUE_DELIMITER,
)
from .question_sets.model import QuestionSet
from .rubrics.model import Rubric, RubricCoverage
from .rules.types import RuleValidationError

# Serializers (registries and types)
from .serializations.base import DataBlob, Dumper, Serializer
from .serializations.registries import (
    question_set_serializer_registry,
    rubric_serializer_registry,
    submissions_serializer_registry,
)
from .submissions.models import RawSubmission, Submission

# ---------------------------
# Discovery helpers
# ---------------------------


def list_available_question_set_serializers() -> list[str]:
    return question_set_serializer_registry.available()


def list_available_rubric_serializers() -> list[str]:
    return rubric_serializer_registry.available()


def list_available_submissions_serializers() -> list[str]:
    return submissions_serializer_registry.available()


def list_available_raw_submissions_adapters() -> list[str]:
    return raw_submissions_adapter_registry.available()


def list_available_question_set_adapters() -> list[str]:
    return question_set_adapter_registry.available()


def list_available_rubric_adapters() -> list[str]:
    return rubric_adapter_registry.available()


# ---------------------------
# Registry getters
# ---------------------------


def get_question_set_serializer_class(name: str) -> type[Serializer[QuestionSet]]:
    return question_set_serializer_registry.get(name)


def get_rubric_serializer_class(name: str) -> type[Serializer[Rubric]]:
    return rubric_serializer_registry.get(name)


def get_submissions_serializer_class(
    name: str,
) -> type[Dumper[Iterable[Submission]]]:
    return submissions_serializer_registry.get(name)


def get_raw_submissions_adapter_class(name: str) -> type[RawSubmissionsAdapter]:
    return raw_submissions_adapter_registry.get(name)


def get_question_set_adapter_class(name: str) -> type[QuestionSetAdapter]:
    return question_set_adapter_registry.get(name)


def get_rubric_adapter_class(name: str) -> type[RubricAdapter]:
    return rubric_adapter_registry.get(name)


# ---------------------------
# Serializer I/O helpers
# ---------------------------


def load_question_set_from_blob(
    blob: DataBlob,
    *,
    serializer_name: str = "yaml",
    serializer_kwargs: dict[str, Any] | None = None,
) -> QuestionSet:
    cls = get_question_set_serializer_class(serializer_name)
    serializer = cls(**(serializer_kwargs or {}))
    return serializer.loads(blob)


def dump_question_set_to_blob(
    qset: QuestionSet,
    *,
    serializer_name: str = "yaml",
    serializer_kwargs: dict[str, Any] | None = None,
) -> DataBlob:
    cls = get_question_set_serializer_class(serializer_name)
    serializer = cls(**(serializer_kwargs or {}))
    return serializer.dumps(qset)


def dump_rubric_to_blob(
    rubric: Rubric,
    *,
    serializer_name: str = "yaml",
    serializer_kwargs: dict[str, Any] | None = None,
) -> DataBlob:
    cls = get_rubric_serializer_class(serializer_name)
    serializer = cls(**(serializer_kwargs or {}))
    return serializer.dumps(rubric)


def load_rubric_from_blob(
    blob: DataBlob,
    *,
    serializer_name: str = "yaml",
    serializer_kwargs: dict[str, Any] | None = None,
) -> Rubric:
    cls = get_rubric_serializer_class(serializer_name)
    serializer = cls(**(serializer_kwargs or {}))
    return serializer.loads(blob)


def dump_submissions_to_blob(
    submissions: Iterable[Submission],
    *,
    serializer_name: str = "csv",
    serializer_kwargs: dict[str, Any] | None = None,
) -> DataBlob:
    cls = get_submissions_serializer_class(serializer_name)
    serializer = cls(**(serializer_kwargs or {}))
    return serializer.dumps(submissions)


# ---------------------------
# Adapter helpers
# ---------------------------


def load_raw_submissions_via_adapter(
    source: DataSource,
    *,
    adapter_name: str = "csv",
    adapter_kwargs: dict[str, Any] | None = None,
) -> list[RawSubmission]:
    cls = get_raw_submissions_adapter_class(adapter_name)
    adapter = cls(**(adapter_kwargs or {}))
    return adapter.load(source)


def load_question_set_via_adapter(
    source: DataSource,
    *,
    adapter_name: str = "examplify",
    adapter_kwargs: dict[str, Any] | None = None,
) -> QuestionSet:
    cls = get_question_set_adapter_class(adapter_name)
    adapter = cls(**(adapter_kwargs or {}))
    return adapter.load(source)


def load_rubric_via_adapter(
    source: DataSource,
    *,
    adapter_name: str = "examplify",
    adapter_kwargs: dict[str, Any] | None = None,
) -> Rubric:
    cls = get_rubric_adapter_class(adapter_name)
    adapter = cls(**(adapter_kwargs or {}))
    return adapter.load(source)


# ---------------------------
# Pipeline
# ---------------------------


class PipelineResult(BaseModel):
    raw_submissions: list[RawSubmission]
    question_set: QuestionSet
    submissions: list[Submission] = Field(default_factory=list[Submission])
    rubric: Rubric | None = None
    validation_errors: list[RuleValidationError] = Field(default_factory=list[RuleValidationError])
    output: DataBlob | None = None
    coverage: RubricCoverage | None = None


def run_pipeline(
    *,
    # Submissions source (choose one; raw_submissions preferred if both provided):
    raw_submissions: list[RawSubmission] | None = None,
    submissions_source: DataSource | None = None,
    submissions_adapter_name: str = "csv",
    submissions_adapter_kwargs: dict[str, Any] | None = None,
    submissions_parser_strict: bool = False,
    # Question set source:
    # Option A: serialized QuestionSet via serializer_name + question_set_source
    question_set_source: DataSource | None = None,
    question_set_serializer_name: str | None = None,
    question_set_serializer_kwargs: dict[str, Any] | None = None,
    # Option B: vendor adapter via adapter_name + question_set_adapter_source
    question_set_adapter_source: DataSource | None = None,
    question_set_adapter_name: str = "examplify",
    question_set_adapter_kwargs: dict[str, Any] | None = None,
    # Inference defaults (used only if neither A nor B provided):
    choice_delimiter: str = DEFAULT_CHOICE_DELIMITER,
    choice_option_limit: int = DEFAULT_CHOICE_OPTION_LIMIT,
    choice_normalize_case: bool = DEFAULT_CHOICE_NORMALIZE_CASE,
    multi_value_delimiter: str = DEFAULT_MULTI_VALUE_DELIMITER,
    empty_marker: str = DEFAULT_EMPTY_MARKER,
    # Rubric source (optional):
    # Option A: serialized Rubric via serializer_name + rubric_source
    rubric_source: DataSource | None = None,
    rubric_serializer_name: str | None = None,
    rubric_serializer_kwargs: dict[str, Any] | None = None,
    # Option B: vendor adapter via adapter_name + rubric_adapter_source
    rubric_adapter_source: DataSource | None = None,
    rubric_adapter_name: str = "examplify",
    rubric_adapter_kwargs: dict[str, Any] | None = None,
    rubric_grading_strict: bool = False,
    rubric_override_results: bool = True,
    rubric_grade_questions_without_rule: bool = True,
    # Optional graded output:
    graded_output_serializer_name: str | None = "csv",
    graded_output_serializer_kwargs: dict[str, Any] | None = None,
    graded_output_sink: DataSink | None = None,
) -> PipelineResult:
    """
    End-to-end pipeline using IO sources/sinks, adapters (for external data), and serializers.
    """
    # Resolve submissions
    if raw_submissions is not None:
        raw_subs = raw_submissions
    elif submissions_source is not None:
        raw_subs = load_raw_submissions_via_adapter(
            submissions_source,
            adapter_name=submissions_adapter_name,
            adapter_kwargs=submissions_adapter_kwargs,
        )
    else:
        raise ConfigurationError(
            "Submissions source is required: provide raw_submissions or submissions_source."
        )

    # Resolve question set: serialized, adapter, or infer
    if question_set_serializer_name and question_set_source is not None:
        qset = load_question_set_from_blob(
            question_set_source.read(),
            serializer_name=question_set_serializer_name,
            serializer_kwargs=question_set_serializer_kwargs,
        )
    elif question_set_adapter_source is not None:
        qset = load_question_set_via_adapter(
            question_set_adapter_source,
            adapter_name=question_set_adapter_name,
            adapter_kwargs=question_set_adapter_kwargs,
        )
    else:
        qset = QuestionSet.infer(
            raw_subs,
            choice_delimiter=choice_delimiter,
            choice_option_limit=choice_option_limit,
            choice_normalize_case=choice_normalize_case,
            multi_value_delimiter=multi_value_delimiter,
            empty_marker=empty_marker,
        )

    # Parse submissions
    submissions: list[Submission] = qset.parse(raw_subs, strict=submissions_parser_strict)

    # Resolve rubric (optional)
    used_rubric: Rubric | None = None
    if rubric_serializer_name and rubric_source is not None:
        used_rubric = load_rubric_from_blob(
            rubric_source.read(),
            serializer_name=rubric_serializer_name,
            serializer_kwargs=rubric_serializer_kwargs,
        )
    elif rubric_adapter_source is not None:
        used_rubric = load_rubric_via_adapter(
            rubric_adapter_source,
            adapter_name=rubric_adapter_name,
            adapter_kwargs=rubric_adapter_kwargs,
        )

    # Validate and grade
    validation_errors: list[RuleValidationError] = []
    coverage: RubricCoverage | None = None

    if used_rubric is not None:
        validation_errors = used_rubric.validate_rubric(qset)
        submissions = used_rubric.grade(
            submissions,
            qset.question_map,
            strict=rubric_grading_strict,
            override_results=rubric_override_results,
            grade_questions_without_rule=rubric_grade_questions_without_rule,
        )
        coverage = used_rubric.get_coverage(qset)

    # Optional serialize graded output
    output: DataBlob | None = None
    if graded_output_serializer_name and submissions:
        output = dump_submissions_to_blob(
            submissions,
            serializer_name=graded_output_serializer_name,
            serializer_kwargs=graded_output_serializer_kwargs,
        )
        if graded_output_sink is not None:
            graded_output_sink.write(output)

    return PipelineResult(
        raw_submissions=raw_subs,
        question_set=qset,
        submissions=submissions,
        rubric=used_rubric,
        validation_errors=validation_errors,
        output=output,
        coverage=coverage,
    )


__all__ = [
    # Discovery
    "list_available_question_set_serializers",
    "list_available_rubric_serializers",
    "list_available_submissions_serializers",
    "list_available_raw_submissions_adapters",
    "list_available_question_set_adapters",
    "list_available_rubric_adapters",
    # Getters
    "get_question_set_serializer_class",
    "get_rubric_serializer_class",
    "get_submissions_serializer_class",
    "get_raw_submissions_adapter_class",
    "get_question_set_adapter_class",
    "get_rubric_adapter_class",
    # Serializer I/O
    "load_question_set_from_blob",
    "dump_question_set_to_blob",
    "dump_rubric_to_blob",
    "load_rubric_from_blob",
    "dump_submissions_to_blob",
    # Pipeline
    "PipelineResult",
    "run_pipeline",
]
