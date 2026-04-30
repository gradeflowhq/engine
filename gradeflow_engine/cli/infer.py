from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel

from ..core import dump_question_set_to_blob, load_raw_submissions_via_adapter
from ..exceptions import GradeFlowError
from ..io.sinks import FileSink
from ..io.sources import FileSource
from ..question_sets.inference import (
    DEFAULT_CHOICE_DELIMITER,
    DEFAULT_CHOICE_NORMALIZE_CASE,
    DEFAULT_CHOICE_OPTION_LIMIT,
    DEFAULT_EMPTY_MARKER,
    DEFAULT_MULTI_VALUE_DELIMITER,
    infer_question_map,
)
from ..question_sets.model import QuestionSet
from . import app, console
from .display import print_question_set
from .utils import parse_kv_pairs


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
    try:
        raw_kwargs: dict[str, Any] = parse_kv_pairs(raw_adapter_kv)
        qset_ser_kwargs: dict[str, Any] = parse_kv_pairs(qset_serializer_kv)

        if point_columns:
            raw_kwargs["point_columns"] = parse_kv_pairs(point_columns, str)

        raw_source = FileSource(submissions_path)
        raw_submissions = load_raw_submissions_via_adapter(
            raw_source,
            adapter_name=raw_submissions_adapter,
            adapter_kwargs=raw_kwargs,
        )

        question_map = infer_question_map(
            raw_submissions,
            choice_delimiter=choice_delimiter,
            choice_option_limit=choice_option_limit,
            choice_normalize_case=choice_normalize_case,
            multi_value_delimiter=multi_value_delimiter,
            empty_marker=empty_marker,
        )
        question_set = QuestionSet(question_map=question_map)

        print_question_set(question_set, title="Inferred Question Set")

        if save:
            blob = dump_question_set_to_blob(
                question_set,
                serializer_name=question_set_serializer,
                serializer_kwargs=qset_ser_kwargs,
            )
            FileSink(save).write(blob)
            final_path = (
                save
                if save.suffix.lower() == f".{blob.extension}"
                else save.with_suffix(f".{blob.extension}")
            )
            console.print(f"[green]Saved inferred question set:[/green] {final_path}")

    except GradeFlowError as error:
        console.print(Panel.fit(str(error), title="Error", border_style="red"))
        raise typer.Exit(code=1) from error
    except Exception as error:
        console.print(Panel.fit(str(error), title="Unexpected Error", border_style="red"))
        raise typer.Exit(code=1) from error
