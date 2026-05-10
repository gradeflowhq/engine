import csv
from io import StringIO
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from ...exceptions import (
    GradeFlowValidationError,
    MalformedCsvRowError,
    MissingStudentIdError,
)
from ...io.sources import DataSource
from ...rules.result import QuestionResult
from ...submissions.models import RawSubmission
from ..base import BaseAdapter
from ..registries import RawSubmissionsAdapter

ORIGINAL_POINTS_RULE_NAME = "Original"


class CsvRawSubmissionsConfig(BaseModel):
    format: Literal["csv"] = "csv"
    student_id_column: str = Field(default="student_id")
    answer_columns: list[str] | None = Field(default=None)
    point_columns: dict[str, str] | None = Field(
        default=None,
        description=(
            "Optional mapping of question_id -> CSV column name containing pre-existing points. "
            "When provided, those questions get pre-populated result_map entries"
        ),
    )


class CsvRawSubmissionsAdapter(
    BaseAdapter[CsvRawSubmissionsConfig, list[RawSubmission]], RawSubmissionsAdapter
):
    name: ClassVar[Literal["csv"]] = "csv"
    config: CsvRawSubmissionsConfig = CsvRawSubmissionsConfig()
    _validation_error_cls = GradeFlowValidationError

    @staticmethod
    def _validate_row_integrity(line_number: int, row: dict[str, Any]) -> None:
        """
        Validates that a dictionary row from csv.DictReader does not contain None values.
        DictReader inserts None when a row has fewer fields than the header.
        """
        missing_cols = [k for k, v in row.items() if v is None]
        if missing_cols:
            raise MalformedCsvRowError(line_number, row, missing_cols)

    def _load(self, source: DataSource) -> list[RawSubmission]:
        blob = source.read()
        text = blob.data.decode("utf-8")
        csv_file = StringIO(text)
        reader = csv.DictReader(csv_file)

        submissions: list[RawSubmission] = []

        for row in reader:
            # 1. Integrity Check: Ensure the row wasn't split by embedded newlines
            self._validate_row_integrity(reader.line_num, row)

            # 2. Extract Student ID
            sid = row.get(self.config.student_id_column)
            if not sid:
                # We pass dict(row) because row is a dict-like object, not a pure dict
                raise MissingStudentIdError(self.config.student_id_column, dict(row))

            # 3. Extract Answers
            if self.config.answer_columns is None:
                # Dynamic mode: use all columns except known non-answer columns
                non_answer_cols = {self.config.student_id_column}
                if self.config.point_columns:
                    non_answer_cols.update(self.config.point_columns.values())

                # Note: v is guaranteed not to be None here due to _validate_row_integrity
                answers = {k: v for k, v in row.items() if k not in non_answer_cols}
            else:
                # Explicit mode: use only specified columns
                answers = {
                    col: str(row.get(col, "")) for col in self.config.answer_columns if col in row
                }

            # 4. Extract Pre-existing Points
            pre_points: dict[str, QuestionResult] = {}
            if self.config.point_columns:
                for question_id, col in self.config.point_columns.items():
                    # Defensive get: ensure we don't strip a None if validation somehow failed
                    val = row.get(col)
                    raw_val = val.strip() if val is not None else ""

                    if raw_val:
                        try:
                            pts = float(raw_val)
                        except ValueError:
                            pts = 0.0
                        pre_points[question_id] = QuestionResult(
                            output=pts,
                            passed=pts > 0,
                            feedback="",
                            rule=ORIGINAL_POINTS_RULE_NAME,
                            points=pts,
                            max_points=pts,
                        )

            submissions.append(
                RawSubmission(student_id=sid, raw_answer_map=answers, result_map=pre_points)
            )
        return submissions
