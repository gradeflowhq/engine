from __future__ import annotations

import sys
from pathlib import Path

import typer
import yaml
from natsort import natsorted
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .question_sets.inference import (
    DEFAULT_CHOICE_DELIMITER,
    DEFAULT_CHOICE_NORMALIZE_CASE,
    DEFAULT_CHOICE_OPTION_LIMIT,
    DEFAULT_EMPTY_MARKER,
    DEFAULT_MULTI_VALUE_DELIMITER,
    infer_question_map,
)
from .question_sets.model import QuestionSet
from .registry import (
    question_set_loader_registry,
    question_set_saver_registry,
    rubric_loader_registry,
    submissions_loader_registry,
    submissions_saver_registry,
)
from .rubrics.model import Rubric, RubricCoverage
from .submissions.loaders.base import BaseSubmissionsLoader
from .submissions.models import GradedSubmission, RawSubmission, Submission
from .submissions.savers.base import BaseSubmissionsSaver

# Fix width to avoid title wrapping in CI/test environments
app = typer.Typer(help="GradeFlow Engine CLI")
console = Console(width=120)


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        console.print(
            Panel.fit(f"Failed to read file: {path}\n{e}", title="Error", border_style="red")
        )
        raise typer.Exit(code=1) from e


def _parse_kv_pairs(pairs: list[str] | None) -> dict[str, object]:
    if not pairs:
        return {}
    result: dict[str, object] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"Expected key=value format, got: {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter(f"Empty key in pair: {item!r}")
        try:
            parsed_value = yaml.safe_load(value)
        except Exception:
            parsed_value = value
        result[key] = parsed_value
    return result


def _build_submissions_loader(
    loader_name: str, *, loader_kwargs: dict[str, object]
) -> BaseSubmissionsLoader:
    loader_cls = submissions_loader_registry.get(loader_name)
    return loader_cls.model_validate(loader_kwargs)


def _build_submissions_saver(
    saver_name: str, *, saver_kwargs: dict[str, object]
) -> BaseSubmissionsSaver:
    saver_cls = submissions_saver_registry.get(saver_name)
    return saver_cls.model_validate(saver_kwargs)


def _load_raw_submissions(
    data: str,
    *,
    loader_name: str,
    loader_kwargs: dict[str, object],
) -> list[RawSubmission]:
    loader = _build_submissions_loader(loader_name, loader_kwargs=loader_kwargs)
    return loader.load(data)


def _load_question_set(data: str, *, loader_name: str) -> QuestionSet:
    loader_cls = question_set_loader_registry.get(loader_name)
    loader = loader_cls()
    return loader.load(data)


def _save_question_set(qset: QuestionSet, *, saver_name: str) -> tuple[str, str]:
    saver_cls = question_set_saver_registry.get(saver_name)
    saver = saver_cls()
    out = saver.save(qset)
    return out.data, out.extension


def _load_rubric(data: str, *, loader_name: str) -> Rubric:
    loader_cls = rubric_loader_registry.get(loader_name)
    loader = loader_cls()
    return loader.load(data)


def _save_graded_submissions(
    graded_submissions: list[GradedSubmission],
    *,
    saver_name: str,
    saver_kwargs: dict[str, object],
) -> tuple[str, str]:
    saver = _build_submissions_saver(saver_name, saver_kwargs=saver_kwargs)
    out = saver.save(graded_submissions)
    return out.data, out.extension


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


def _print_grades(graded_submissions: list[GradedSubmission]) -> None:
    if not graded_submissions:
        return
    console.rule("Graded Submissions")
    table = Table(box=box.SIMPLE)
    table.add_column("Student ID", style="green", no_wrap=True)
    table.add_column("Total Points", justify="right", no_wrap=True)
    table.add_column("Max Points", justify="right", no_wrap=True)
    for gs in graded_submissions:
        total_points = sum(r.points for r in gs.results)
        total_max = sum(r.max_points for r in gs.results)
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

    # Details: covered vs uncovered question IDs
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
    List available loaders and savers registered in the engine.
    """
    sections = [
        ("Question Set Loaders", question_set_loader_registry.available()),
        ("Question Set Savers", question_set_saver_registry.available()),
        ("Rubric Loaders", rubric_loader_registry.available()),
        ("Submissions Loaders", submissions_loader_registry.available()),
        ("Submissions Savers", submissions_saver_registry.available()),
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
    submissions_loader_name: str = typer.Option(
        "CSV", "--submissions-loader", help="Registry key for submissions loader (e.g., 'CSV')"
    ),
    submissions_loader_kv: list[str] | None = typer.Option(
        None,
        "--submissions-loader-kv",
        help=(
            "Repeatable key=value pairs for submissions loader configuration "
            "(e.g., student_id_column=id, answer_columns=[Q1,Q2])"
        ),
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
        help="Whether to normalize case for Choice inference",
    ),
    multi_value_delimiter: str = typer.Option(
        DEFAULT_MULTI_VALUE_DELIMITER,
        "--multi-value-delimiter",
        help="Delimiter for Multi-Valued inference",
    ),
    empty_marker: str = typer.Option(
        DEFAULT_EMPTY_MARKER,
        "--empty-marker",
        help="Marker indicating an empty answer",
    ),
    save: Path | None = typer.Option(
        None, "--save", help="Path to save the inferred question set (YAML)."
    ),
    question_set_saver_name: str = typer.Option(
        "YAML", "--question-set-saver", help="Registry key for question set saver (e.g., 'YAML')"
    ),
) -> None:
    """
    Infer a question set from submissions and print a summary. Optionally save to a file.
    """
    try:
        submissions_data = _read_text_file(submissions_path)
        loader_kwargs = _parse_kv_pairs(submissions_loader_kv)

        raw_subs = _load_raw_submissions(
            submissions_data,
            loader_name=submissions_loader_name,
            loader_kwargs=loader_kwargs,
        )

        # Inference via infer_question_map to build QuestionSet explicitly
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
            data, ext = _save_question_set(qset, saver_name=question_set_saver_name)
            final_path = save
            if final_path.suffix.lower() != f".{ext.lower()}":
                final_path = final_path.with_suffix(f".{ext}")
            final_path.write_text(data, encoding="utf-8")
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
    submissions_loader_name: str = typer.Option(
        "CSV", "--submissions-loader", help="Registry key for submissions loader (e.g., 'CSV')"
    ),
    submissions_loader_kv: list[str] | None = typer.Option(
        None,
        "--submissions-loader-kv",
        help=(
            "Repeatable key=value pairs for submissions loader configuration "
            "(e.g., student_id_column=id, answer_columns=[Q1,Q2])"
        ),
    ),
    submissions_parser_strict: bool = typer.Option(
        False,
        "--submissions-parser-strict/--no-submissions-parser-strict",
        help="Whether to fail on parsing errors when parsing submissions.",
    ),
    # Question set
    question_set_path: Path | None = typer.Option(
        None, "--question-set", help="Path to question set file (e.g., YAML). If omitted, infer."
    ),
    question_set_loader_name: str = typer.Option(
        "YAML", "--question-set-loader", help="Registry key for question set loader (e.g., 'YAML')"
    ),
    choice_delimiter: str = typer.Option(
        DEFAULT_CHOICE_DELIMITER, "--choice-delimiter", help="Choice delimiter for inference"
    ),
    choice_option_limit: int = typer.Option(
        DEFAULT_CHOICE_OPTION_LIMIT,
        "--choice-option-limit",
        help="Max distinct choices for Choice inference",
    ),
    choice_normalize_case: bool = typer.Option(
        DEFAULT_CHOICE_NORMALIZE_CASE,
        "--choice-normalize-case",
        help="Whether to normalize case for Choice inference",
    ),
    multi_value_delimiter: str = typer.Option(
        DEFAULT_MULTI_VALUE_DELIMITER,
        "--multi-value-delimiter",
        help="Delimiter for Multi-Valued inference",
    ),
    empty_marker: str = typer.Option(
        DEFAULT_EMPTY_MARKER,
        "--empty-marker",
        help="Marker indicating an empty answer",
    ),
    # Rubric
    rubric_path: Path | None = typer.Option(
        None, "--rubric", help="Path to rubric file (e.g., YAML). If omitted, grading is skipped."
    ),
    rubric_loader_name: str = typer.Option(
        "YAML", "--rubric-loader", help="Registry key for rubric loader (e.g., 'YAML')"
    ),
    # Grading
    rubric_grading_strict: bool = typer.Option(
        False,
        "--rubric-grading-strict/--no-rubric-grading-strict",
        help="Whether to fail on errors during rubric grading.",
    ),
    # Saver
    saver_name: str | None = typer.Option(
        "CSV", "--saver", help="Registry key for submissions saver (e.g., 'CSV')"
    ),
    saver_kv: list[str] | None = typer.Option(
        None,
        "--saver-kv",
        help=(
            "Repeatable key=value pairs for submissions saver configuration "
            "(e.g., student_id_column=id, include_answers=true)"
        ),
    ),
    output_path: Path | None = typer.Option(
        None,
        "--out",
        help="Write saved graded submissions to this file (extension inferred from saver)",
    ),
) -> None:
    """
    Grade submissions using a question set (loaded or inferred) and an optional rubric.
    Prints a summary and optionally saves the graded results.
    """
    try:
        submissions_data = _read_text_file(submissions_path)
        loader_kwargs = _parse_kv_pairs(submissions_loader_kv)

        raw_subs = _load_raw_submissions(
            submissions_data,
            loader_name=submissions_loader_name,
            loader_kwargs=loader_kwargs,
        )

        # Resolve QuestionSet: load from file or infer
        if question_set_path is not None:
            qset_data = _read_text_file(question_set_path)
            qset = _load_question_set(qset_data, loader_name=question_set_loader_name)
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
        used_rubric: Rubric | None = None
        if rubric_path is not None:
            rubric_data = _read_text_file(rubric_path)
            used_rubric = _load_rubric(rubric_data, loader_name=rubric_loader_name)

        # Validate and grade
        validation_errors: list[str] = []
        graded: list[GradedSubmission] = []
        coverage: RubricCoverage | None = None
        if used_rubric is not None:
            validation_errors = used_rubric.validate_rubric(qset)
            coverage = used_rubric.get_coverage(qset)
            if not validation_errors:
                graded = used_rubric.grade(submissions, strict=rubric_grading_strict)

        # Output summaries
        _print_question_set(qset, title="Question Set")
        _print_submissions(submissions)
        _print_validation_errors(validation_errors)
        if coverage is not None:
            _print_coverage(coverage)
        _print_grades(graded)

        # Save graded submissions if requested and grading occurred
        if saver_name and graded:
            saver_kwargs = _parse_kv_pairs(saver_kv)
            data, ext = _save_graded_submissions(
                graded,
                saver_name=saver_name,
                saver_kwargs=saver_kwargs,
            )
            console.print(
                Panel.fit(f"Generated output ({ext})", title="Save", border_style="green")
            )
            if output_path:
                final_path = output_path
                if final_path.suffix.lower() != f".{ext.lower()}":
                    final_path = final_path.with_suffix(f".{ext}")
                final_path.write_text(data, encoding="utf-8")
                console.print(f"[green]Saved:[/green] {final_path}")
            else:
                sys.stdout.write(data)

    except Exception as e:
        console.print(Panel.fit(str(e), title="Error", border_style="red"))
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
