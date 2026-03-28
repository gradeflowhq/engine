import sys
from pathlib import Path

import typer
import yaml
from natsort import natsorted
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import (
    dump_question_set_to_blob,
    dump_submissions_to_blob,
    list_available_question_set_adapters,
    # discovery
    list_available_question_set_serializers,
    list_available_raw_submissions_adapters,
    list_available_rubric_adapters,
    list_available_rubric_serializers,
    list_available_submissions_serializers,
    # I/O helpers
    load_question_set_from_blob,
    load_question_set_via_adapter,
    load_raw_submissions_via_adapter,
    load_rubric_from_blob,
    load_rubric_via_adapter,
)
from .io.sinks import FileSink
from .io.sources import FileSource
from .question_sets.inference import (
    DEFAULT_CHOICE_DELIMITER,
    DEFAULT_CHOICE_NORMALIZE_CASE,
    DEFAULT_CHOICE_OPTION_LIMIT,
    DEFAULT_EMPTY_MARKER,
    DEFAULT_MULTI_VALUE_DELIMITER,
    infer_question_map,
)
from .question_sets.model import QuestionSet
from .rubrics.model import RubricCoverage
from .submissions.models import Submission

# Fix width to avoid title wrapping in CI/test environments
app = typer.Typer(help="GradeFlow Engine CLI")
console = Console(width=120)


def _parse_kv_pairs(pairs: list[str] | None) -> dict[str, object]:
    """
    Parse key=value pairs into a dict[str, object].
    Values are parsed via yaml.safe_load to support ints/bools/lists.
    """
    if not pairs:
        return {}
    out: dict[str, object] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"Expected key=value, got: {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        try:
            out[key] = yaml.safe_load(value)
        except Exception:
            out[key] = value
    return out


def _parse_str_kv_pairs(pairs: list[str] | None) -> dict[str, str]:
    """
    Parse key=value pairs into a dict[str, str].
    Values are kept as plain strings (no YAML coercion), suitable for column name mappings.
    """
    if not pairs:
        return {}
    out: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"Expected key=value, got: {item!r}")
        key, value = item.split("=", 1)
        out[key.strip()] = value
    return out


def _print_question_set(qset: QuestionSet, title: str = "Question Set") -> None:
    console.rule(title)
    table = Table(box=box.SIMPLE)
    table.add_column("Question ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta", no_wrap=True)
    for qid, q in qset.question_map.items():
        table.add_row(qid, q.type)  # type: ignore[attr-defined]
    console.print(table)


def _print_submissions(submissions: list[Submission]) -> None:
    console.rule("Parsed Submissions")
    table = Table(box=box.SIMPLE)
    table.add_column("Student ID", style="green", no_wrap=True)
    table.add_column("# Answers", justify="right", no_wrap=True)
    for s in submissions:
        table.add_row(s.student_id, str(len(s.answer_map)))
    console.print(table)


def _print_validation_errors(errors: list[str]) -> None:
    if not errors:
        return
    console.rule("Rubric Validation Errors")
    table = Table(box=box.SIMPLE)
    table.add_column("Error", style="red")
    for err in errors:
        table.add_row(err)
    console.print(table)


def _print_grades(submissions: list[Submission]) -> None:
    if not submissions:
        return
    console.rule("Graded Submissions")
    table = Table(box=box.SIMPLE)
    table.add_column("Student ID", style="green", no_wrap=True)
    table.add_column("Total Points", justify="right", no_wrap=True)
    table.add_column("Max Points", justify="right", no_wrap=True)
    for gs in submissions:
        total_points = sum(r.points for r in gs.result_map.values())
        total_max = sum(r.max_points for r in gs.result_map.values())
        table.add_row(gs.student_id, f"{total_points:.2f}", f"{total_max:.2f}")
    console.print(table)


def _print_coverage(coverage: RubricCoverage) -> None:
    console.rule("Rubric Coverage")
    summary = Table(box=box.SIMPLE)
    summary.add_column("Total Questions", justify="right", no_wrap=True)
    summary.add_column("Covered by Rubric", justify="right", no_wrap=True)
    summary.add_column("Coverage", justify="right", no_wrap=True)
    summary.add_row(str(coverage.total), str(coverage.covered), f"{coverage.percentage:.0%}")
    console.print(summary)

    covered_ids = natsorted(coverage.covered_question_ids)
    uncovered_ids = natsorted(coverage.question_ids - coverage.covered_question_ids)

    details = Table(box=box.SIMPLE)
    details.add_column("Covered IDs", style="green")
    details.add_column("Uncovered IDs", style="red")
    details.add_row(
        ", ".join(covered_ids) if covered_ids else "<none>",
        ", ".join(uncovered_ids) if uncovered_ids else "<none>",
    )
    console.print(details)


@app.command("list")
def list_components() -> None:
    """
    List available serializers and adapters registered in the engine.
    """
    sections = [
        ("Question Set Serializers", list_available_question_set_serializers()),
        ("Rubric Serializers", list_available_rubric_serializers()),
        ("Graded Submissions Serializers", list_available_submissions_serializers()),
        ("Raw Submissions Adapters", list_available_raw_submissions_adapters()),
        ("Question Set Adapters", list_available_question_set_adapters()),
        ("Rubric Adapters", list_available_rubric_adapters()),
    ]
    for title, items in sections:
        console.rule(title)
        table = Table(box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column("Name", style="cyan", no_wrap=True)
        if items:
            for name in items:
                table.add_row(name)
        else:
            table.add_row("<none>")
        console.print(table)


@app.command("infer")
def infer_questions(
    submissions_path: Path = typer.Argument(..., help="Path to submissions file (e.g., CSV)"),
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
    choice_delimiter: str = typer.Option(
        DEFAULT_CHOICE_DELIMITER,
        "--choice-delimiter",
        help="Choice delimiter used during inference",
    ),
    choice_option_limit: int = typer.Option(
        DEFAULT_CHOICE_OPTION_LIMIT,
        "--choice-option-limit",
        help="Max distinct choices for Choice inference",
    ),
    choice_normalize_case: bool = typer.Option(
        DEFAULT_CHOICE_NORMALIZE_CASE,
        "--choice-normalize-case",
        help="Normalize case for Choice inference",
    ),
    multi_value_delimiter: str = typer.Option(
        DEFAULT_MULTI_VALUE_DELIMITER,
        "--multi-value-delimiter",
        help="Delimiter for Multi-Valued inference",
    ),
    empty_marker: str = typer.Option(
        DEFAULT_EMPTY_MARKER, "--empty-marker", help="Marker indicating an empty answer"
    ),
    save: Path | None = typer.Option(
        None,
        "--save",
        help="Path to save the inferred question set (extension adjusted by serializer)",
    ),
    question_set_serializer: str = typer.Option(
        "yaml",
        "--question-set-serializer",
        help="Serializer key for question set output (e.g., 'yaml')",
    ),
    qset_serializer_kv: list[str] | None = typer.Option(
        None,
        "--question-set-serializer-config",
        help="key=value for question set serializer (repeatable)",
    ),
) -> None:
    """
    Infer a question set from submissions and print a summary. Optionally save to a file.
    """
    try:
        raw_kwargs = _parse_kv_pairs(raw_adapter_kv)
        qset_ser_kwargs = _parse_kv_pairs(qset_serializer_kv)

        if point_columns:
            raw_kwargs["point_columns"] = _parse_str_kv_pairs(point_columns)

        raw_src = FileSource(submissions_path)
        raw_subs = load_raw_submissions_via_adapter(
            raw_src, adapter_name=raw_submissions_adapter, adapter_kwargs=raw_kwargs
        )

        qmap = infer_question_map(
            raw_subs,
            choice_delimiter=choice_delimiter,
            choice_option_limit=choice_option_limit,
            choice_normalize_case=choice_normalize_case,
            multi_value_delimiter=multi_value_delimiter,
            empty_marker=empty_marker,
        )
        qset = QuestionSet(question_map=qmap)

        _print_question_set(qset, title="Inferred Question Set")

        if save:
            blob = dump_question_set_to_blob(
                qset,
                serializer_name=question_set_serializer,
                serializer_kwargs=qset_ser_kwargs,
            )
            sink = FileSink(save)
            sink.write(blob)
            final_path = (
                save
                if save.suffix.lower() == f".{blob.extension}"
                else save.with_suffix(f".{blob.extension}")
            )
            console.print(f"[green]Saved inferred question set:[/green] {final_path}")

    except Exception as e:
        console.print(Panel.fit(str(e), title="Error", border_style="red"))
        raise typer.Exit(code=1) from e


@app.command("grade")
def grade(
    # Submissions
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
    # Question set
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
    # Inference params if neither serialized qset nor adapter src provided
    choice_delimiter: str = typer.Option(DEFAULT_CHOICE_DELIMITER, "--choice-delimiter"),
    choice_option_limit: int = typer.Option(DEFAULT_CHOICE_OPTION_LIMIT, "--choice-option-limit"),
    choice_normalize_case: bool = typer.Option(
        DEFAULT_CHOICE_NORMALIZE_CASE, "--choice-normalize-case"
    ),
    multi_value_delimiter: str = typer.Option(
        DEFAULT_MULTI_VALUE_DELIMITER, "--multi-value-delimiter"
    ),
    empty_marker: str = typer.Option(DEFAULT_EMPTY_MARKER, "--empty-marker"),
    # Rubric
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
    # Output
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
    """
    Grade submissions using a question set (serialized or adapted) and an optional rubric
    (serialized or adapted). Prints a summary and optionally saves the graded results.
    """
    try:
        # Parse kv configs
        raw_kwargs = _parse_kv_pairs(raw_adapter_kv)
        qset_ser_kwargs = _parse_kv_pairs(qset_serializer_kv)
        qset_ad_kwargs = _parse_kv_pairs(qset_adapter_kv)
        rubric_ser_kwargs = _parse_kv_pairs(rubric_serializer_kv)
        rubric_ad_kwargs = _parse_kv_pairs(rubric_adapter_kv)
        out_ser_kwargs = _parse_kv_pairs(out_serializer_kv)

        if point_columns:
            raw_kwargs["point_columns"] = _parse_str_kv_pairs(point_columns)

        # Load raw submissions
        raw_src = FileSource(submissions_path)
        raw_subs = load_raw_submissions_via_adapter(
            raw_src, adapter_name=raw_submissions_adapter, adapter_kwargs=raw_kwargs
        )

        # Resolve QuestionSet
        if question_set_path is not None:
            qset_blob = FileSource(question_set_path).read()
            qset = load_question_set_from_blob(
                qset_blob,
                serializer_name=question_set_serializer,
                serializer_kwargs=qset_ser_kwargs,
            )
        elif question_set_adapter_path is not None:
            qset = load_question_set_via_adapter(
                FileSource(question_set_adapter_path),
                adapter_name=question_set_adapter,
                adapter_kwargs=qset_ad_kwargs,
            )
        else:
            qmap = infer_question_map(
                raw_subs,
                choice_delimiter=choice_delimiter,
                choice_option_limit=choice_option_limit,
                choice_normalize_case=choice_normalize_case,
                multi_value_delimiter=multi_value_delimiter,
                empty_marker=empty_marker,
            )
            qset = QuestionSet(question_map=qmap)

        # Parse submissions
        submissions: list[Submission] = qset.parse(raw_subs, strict=submissions_parser_strict)

        # Resolve Rubric (optional)
        used_rubric = None
        if rubric_path is not None:
            rubric_blob = FileSource(rubric_path).read()
            used_rubric = load_rubric_from_blob(
                rubric_blob, serializer_name=rubric_serializer, serializer_kwargs=rubric_ser_kwargs
            )
        elif rubric_adapter_path is not None:
            used_rubric = load_rubric_via_adapter(
                FileSource(rubric_adapter_path),
                adapter_name=rubric_adapter,
                adapter_kwargs=rubric_ad_kwargs,
            )

        # Validate and grade
        validation_errors: list[str] = []
        graded: list[Submission] = []
        coverage: RubricCoverage | None = None
        if used_rubric is not None:
            validation_errors = used_rubric.validate_rubric(qset)
            coverage = used_rubric.get_coverage(qset)
            if not validation_errors:
                graded = used_rubric.grade(
                    submissions, qset.question_map, strict=rubric_grading_strict
                )

        # Output summaries
        _print_question_set(qset, title="Question Set")
        _print_submissions(submissions)
        _print_validation_errors(validation_errors)
        if coverage is not None:
            _print_coverage(coverage)

        if graded:
            _print_grades(graded)

        # Save graded submissions if requested and grading occurred
        if graded and graded_serializer:
            blob = dump_submissions_to_blob(
                graded, serializer_name=graded_serializer, serializer_kwargs=out_ser_kwargs
            )
            if output_path:
                sink = FileSink(output_path)
                sink.write(blob)
                final_path = (
                    output_path
                    if output_path.suffix.lower() == f".{blob.extension}"
                    else output_path.with_suffix(f".{blob.extension}")
                )
                console.print(f"[green]Saved:[/green] {final_path}")
            else:
                # If no path, print to stdout for convenience (text formats)
                if blob.media_type.startswith("text/") or blob.media_type in (
                    "application/json",
                    "application/yaml",
                ):
                    sys.stdout.write(blob.data.decode("utf-8"))
                else:
                    console.print(
                        Panel.fit(
                            "Binary output generated; please specify --out to save to a file.",
                            title="Notice",
                            border_style="yellow",
                        )
                    )

    except Exception as e:
        console.print(Panel.fit(str(e), title="Error", border_style="red"))
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
