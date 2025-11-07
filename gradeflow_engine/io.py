"""
Input/Output utilities for loading and saving data.

Handles loading rubrics from YAML, submissions from CSV, and saving results.
Also supports loading and saving assessment schemas.
"""

import csv
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .exports import ExportConfig, export_registry
from .models import GradeOutput, Rubric, Submission
from .schema import AssessmentSchema


# Helper functions to reduce duplication
def _ensure_parent_dir(file_path: str) -> Path:
    """Ensure parent directory exists and return Path object."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _save_yaml(data: dict[str, Any], file_path: str, indent: int = 2) -> None:
    """Save dictionary to YAML file."""
    path = _ensure_parent_dir(file_path)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=indent)


def load_rubric(file_path: str) -> Rubric:
    """
    Load a rubric from a YAML file.

    Args:
        file_path: Path to YAML file containing rubric (.yaml or .yml)

    Returns:
        Rubric object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML is invalid or doesn't match schema
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Rubric file not found: {file_path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format in {file_path}: {str(e)}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to read rubric file {file_path}: {str(e)}") from e

    try:
        return Rubric.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid rubric format in {file_path}: {str(e)}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error validating rubric: {str(e)}") from e


def save_rubric(rubric: Rubric, file_path: str, indent: int = 2) -> None:
    """
    Save a rubric to a YAML file.

    Args:
        rubric: Rubric object to save
        file_path: Path to output YAML file
        indent: Indentation (default 2)
    """
    data = rubric.model_dump(mode="json")
    _save_yaml(data, file_path, indent)


def load_submissions_csv(
    file_path: str,
    student_id_col: str = "student_id",
    encoding: str = "utf-8",
    validate_questions: list[str] | None = None,
) -> list[Submission]:
    """
    Load student submissions from a CSV file.

    The CSV should have a column for student ID and columns for each question.
    Question columns can be named anything (e.g., Q1, Q2, question_1, etc.).

    Args:
        file_path: Path to CSV file
        student_id_col: Name of the student ID column (default: "student_id")
        encoding: File encoding (default: "utf-8")
        validate_questions: Optional list of required question IDs to validate against

    Returns:
        List of Submission objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If CSV is invalid or missing required columns
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Submissions file not found: {file_path}")

    submissions: list[Submission] = []

    with open(path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header row")

        if student_id_col not in reader.fieldnames:
            raise ValueError(f"Student ID column '{student_id_col}' not found in CSV")

        # Validate question columns if requested
        if validate_questions:
            csv_questions = set(reader.fieldnames) - {student_id_col}
            required_questions = set(validate_questions)
            missing = required_questions - csv_questions
            if missing:
                raise ValueError(
                    f"CSV missing required question columns: {', '.join(sorted(missing))}"
                )

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            student_id = row.get(student_id_col, "").strip()

            if not student_id:
                raise ValueError(f"Missing student ID in row {row_num}")

            # Extract all columns except student_id as answers
            answers = {
                key: value.strip()
                for key, value in row.items()
                if key != student_id_col and value is not None
            }

            submissions.append(
                Submission(
                    student_id=student_id,
                    answers=answers,
                    metadata={"row_number": row_num},
                )
            )

    return submissions


def export_results(results: "GradeOutput", file_path: Path | str, config: "ExportConfig"):
    """Export GradeOutput using the configured exporter.

    Resolves the appropriate exporter via the exports registry and calls it.
    """
    entry = export_registry.get_by_config(type(config) if not isinstance(config, type) else config)
    func = entry["func"]
    return func(results, file_path, config)


# ============================================================================
# Schema I/O
# ============================================================================


def load_schema(file_path: str) -> AssessmentSchema:
    """
    Load an assessment schema from a YAML file.

    Args:
        file_path: Path to YAML file containing schema (.yaml or .yml)

    Returns:
        AssessmentSchema object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML is invalid or doesn't match schema
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {file_path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML format in {file_path}")

        return AssessmentSchema.model_validate(data)

    except ValidationError as e:
        raise ValueError(f"Schema validation failed: {e}") from e
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {file_path}: {e}") from e


def save_schema(schema: AssessmentSchema, file_path: str, indent: int = 2) -> None:
    """
    Save an assessment schema to a YAML file.

    Args:
        schema: AssessmentSchema to save
        file_path: Path to save schema YAML file (.yaml or .yml)
        indent: YAML indentation level (default: 2)

    Example:
        >>> schema = AssessmentSchema(name="Midterm", questions={...})
        >>> save_schema(schema, "assessment_schema.yaml")
    """
    data = schema.model_dump(mode="python", exclude_none=True)
    _save_yaml(data, file_path, indent)
