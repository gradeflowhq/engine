import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel

from ..core import run_pipeline
from ..exceptions import GradeFlowError
from ..io.sinks import FileSink, StringSink
from ..io.sources import FileSource
from ..question_sets.inference import (
    DEFAULT_CHOICE_DELIMITER,
    DEFAULT_CHOICE_NORMALIZE_CASE,
    DEFAULT_CHOICE_OPTION_LIMIT,
    DEFAULT_EMPTY_MARKER,
    DEFAULT_MULTI_VALUE_DELIMITER,
)
from . import app, console
from .display import (
    print_coverage,
    print_grades,
    print_question_set,
    print_submissions,
    print_validation_errors,
)
from .utils import parse_kv_pairs


class RubricGradingParallelMode(StrEnum):
    processes = "processes"
    threads = "threads"


@app.command("grade")
def grade(
    submissions_path: Path = typer.Option(
        ..., "--submissions", help="Path to submissions file (e.g., CSV)."
    ),
    raw_submissions_adapter: str = typer.Option(
        "csv", "--raw-submissions-adapter", help="Adapter key for raw submissions (e.g., 'csv')"
    ),
    raw_adapter_kv: list[str] | None = typer.Option(
        None,
        "--raw-submissions-adapter-config",
        help="key=value for raw adapter config (repeatable)",
    ),
    point_columns: list[str] | None = typer.Option(
        None,
        "--point-column",
        help="question_id=csv_column mapping for pass-through point columns (repeatable)",
    ),
    submissions_parser_strict: bool = typer.Option(
        False,
        "--submissions-parser-strict/--no-submissions-parser-strict",
        help="Whether to fail on parsing errors when parsing submissions.",
    ),
    question_set_path: Path | None = typer.Option(
        None, "--question-set", help="Path to serialized question set (e.g., YAML)."
    ),
    question_set_serializer: str = typer.Option(
        "yaml",
        "--question-set-serializer",
        help="Serializer key for question set input (e.g., 'yaml')",
    ),
    qset_serializer_kv: list[str] | None = typer.Option(
        None, "--question-set-serializer-config", help="key=value for qset serializer (repeatable)"
    ),
    question_set_adapter_path: Path | None = typer.Option(
        None,
        "--question-set-adapter-src",
        help="Path to a vendor source for question set (e.g., Examplify CSV).",
    ),
    question_set_adapter: str = typer.Option(
        "examplify",
        "--question-set-adapter",
        help="Adapter key for question set vendor source (e.g., 'examplify')",
    ),
    qset_adapter_kv: list[str] | None = typer.Option(
        None, "--question-set-adapter-config", help="key=value for qset adapter config (repeatable)"
    ),
    choice_delimiter: str = typer.Option(DEFAULT_CHOICE_DELIMITER, "--choice-delimiter"),
    choice_option_limit: int = typer.Option(DEFAULT_CHOICE_OPTION_LIMIT, "--choice-option-limit"),
    choice_normalize_case: bool = typer.Option(
        DEFAULT_CHOICE_NORMALIZE_CASE, "--choice-normalize-case"
    ),
    multi_value_delimiter: str = typer.Option(
        DEFAULT_MULTI_VALUE_DELIMITER, "--multi-value-delimiter"
    ),
    empty_marker: str = typer.Option(DEFAULT_EMPTY_MARKER, "--empty-marker"),
    rubric_path: Path | None = typer.Option(
        None,
        "--rubric",
        help="Path to serialized rubric (e.g., YAML). If omitted, grading is skipped.",
    ),
    rubric_serializer: str = typer.Option(
        "yaml", "--rubric-serializer", help="Serializer key for rubric input (e.g., 'yaml')"
    ),
    rubric_serializer_kv: list[str] | None = typer.Option(
        None, "--rubric-serializer-config", help="key=value for rubric serializer (repeatable)"
    ),
    rubric_adapter_path: Path | None = typer.Option(
        None,
        "--rubric-adapter-src",
        help="Path to a vendor source for rubric (e.g., Examplify CSV).",
    ),
    rubric_adapter: str = typer.Option(
        "examplify",
        "--rubric-adapter",
        help="Adapter key for rubric vendor source (e.g., 'examplify')",
    ),
    rubric_adapter_kv: list[str] | None = typer.Option(
        None, "--rubric-adapter-config", help="key=value for rubric adapter config (repeatable)"
    ),
    rubric_grading_strict: bool = typer.Option(
        False,
        "--rubric-grading-strict/--no-rubric-grading-strict",
        help="Whether to fail on errors during rubric grading.",
    ),
    rubric_override_results: bool = typer.Option(
        True,
        "--rubric-override-results/--no-rubric-override-results",
        help=(
            "When enabled (default), rule results overwrite pre-existing results "
            "for covered questions. When disabled, questions that already have a "
            "result (e.g. pass-through points from --point-column) are left untouched."
        ),
    ),
    rubric_grade_questions_without_rule: bool = typer.Option(
        True,
        "--rubric-grade-questions-without-rule/--no-rubric-grade-questions-without-rule",
        help=(
            "When enabled (default), questions in the question map that are not "
            "covered by any rule and have no existing result receive a zero-point "
            "result. When disabled, such questions are omitted from result_map entirely."
        ),
    ),
    rubric_grading_parallel_jobs: int = typer.Option(
        1,
        "--rubric-grading-parallel-jobs",
        help=(
            "Number of parallel workers to use for rubric grading. Use -1 for all CPUs "
            "available to the process, capped by submission count."
        ),
    ),
    rubric_grading_parallel_mode: RubricGradingParallelMode = typer.Option(
        "processes",
        "--rubric-grading-parallel-mode",
        help="Worker mode for parallel rubric grading.",
    ),
    graded_serializer: str = typer.Option(
        "csv",
        "--out-serializer",
        help="Serializer key for graded submissions output (csv|json|yaml)",
    ),
    out_serializer_kv: list[str] | None = typer.Option(
        None, "--out-serializer-config", help="key=value for output serializer (repeatable)"
    ),
    output_path: Path | None = typer.Option(
        None,
        "--out",
        help="Write graded submissions to this file (extension inferred from serializer)",
    ),
) -> None:
    try:
        raw_kwargs: dict[str, Any] = parse_kv_pairs(raw_adapter_kv)
        qset_ser_kwargs: dict[str, Any] = parse_kv_pairs(qset_serializer_kv)
        qset_ad_kwargs: dict[str, Any] = parse_kv_pairs(qset_adapter_kv)
        rubric_ser_kwargs: dict[str, Any] = parse_kv_pairs(rubric_serializer_kv)
        rubric_ad_kwargs: dict[str, Any] = parse_kv_pairs(rubric_adapter_kv)
        out_ser_kwargs: dict[str, Any] = parse_kv_pairs(out_serializer_kv)

        if point_columns:
            raw_kwargs["point_columns"] = parse_kv_pairs(point_columns, str)

        has_rubric_source = rubric_path is not None or rubric_adapter_path is not None
        output_sink = FileSink(output_path) if output_path and has_rubric_source else None

        result = run_pipeline(
            submissions_source=FileSource(submissions_path),
            submissions_adapter_name=raw_submissions_adapter,
            submissions_adapter_kwargs=raw_kwargs,
            submissions_parser_strict=submissions_parser_strict,
            question_set_source=FileSource(question_set_path) if question_set_path else None,
            question_set_serializer_name=question_set_serializer if question_set_path else None,
            question_set_serializer_kwargs=qset_ser_kwargs,
            question_set_adapter_source=(
                FileSource(question_set_adapter_path) if question_set_adapter_path else None
            ),
            question_set_adapter_name=question_set_adapter,
            question_set_adapter_kwargs=qset_ad_kwargs,
            choice_delimiter=choice_delimiter,
            choice_option_limit=choice_option_limit,
            choice_normalize_case=choice_normalize_case,
            multi_value_delimiter=multi_value_delimiter,
            empty_marker=empty_marker,
            rubric_source=FileSource(rubric_path) if rubric_path else None,
            rubric_serializer_name=rubric_serializer if rubric_path else None,
            rubric_serializer_kwargs=rubric_ser_kwargs,
            rubric_adapter_source=(
                FileSource(rubric_adapter_path) if rubric_adapter_path else None
            ),
            rubric_adapter_name=rubric_adapter,
            rubric_adapter_kwargs=rubric_ad_kwargs,
            rubric_grading_strict=rubric_grading_strict,
            rubric_override_results=rubric_override_results,
            rubric_grade_questions_without_rule=rubric_grade_questions_without_rule,
            rubric_grading_parallel_jobs=rubric_grading_parallel_jobs,
            rubric_grading_parallel_mode=rubric_grading_parallel_mode.value,
            graded_output_serializer_name=graded_serializer if has_rubric_source else None,
            graded_output_serializer_kwargs=out_ser_kwargs,
            graded_output_sink=output_sink,
        )

        print_question_set(result.question_set, title="Question Set")
        print_submissions(result.submissions)
        print_validation_errors(result.validation_errors)
        if result.coverage is not None:
            print_coverage(result.coverage)

        if result.rubric is not None and result.submissions:
            print_grades(result.submissions)

        if result.output is not None:
            if output_path:
                final_path = (
                    output_path
                    if output_path.suffix.lower() == f".{result.output.extension}"
                    else output_path.with_suffix(f".{result.output.extension}")
                )
                console.print(f"[green]Saved:[/green] {final_path}")
            elif result.output.media_type.startswith("text/") or result.output.media_type in (
                "application/json",
                "application/yaml",
            ):
                sink = StringSink()
                sink.write(result.output)
                sys.stdout.write(sink.data)
            else:
                console.print(
                    Panel.fit(
                        "Binary output generated; please specify --out to save to a file.",
                        title="Notice",
                        border_style="yellow",
                    )
                )

    except GradeFlowError as error:
        console.print(Panel.fit(str(error), title="Error", border_style="red"))
        raise typer.Exit(code=1) from error
    except Exception as error:
        console.print(Panel.fit(str(error), title="Unexpected Error", border_style="red"))
        raise typer.Exit(code=1) from error
