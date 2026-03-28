import csv
from io import StringIO
from typing import Literal

from pydantic import BaseModel, Field

from ...io.sources import DataSource
from ...rules.result import QuestionResult
from ...submissions.models import RawSubmission
from ..registries import RawSubmissionsAdapter, raw_submissions_adapter_registry

ORIGINAL_POINTS_RULE_NAME = "Original"


class CsvRawSubmissionsConfig(BaseModel):
    name: Literal["csv"] = "csv"
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


class CsvRawSubmissionsAdapter(RawSubmissionsAdapter):
    name: Literal["csv"] = "csv"
    config: CsvRawSubmissionsConfig = CsvRawSubmissionsConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def load(self, source: DataSource) -> list[RawSubmission]:
        blob = source.read()
        text = blob.data.decode("utf-8")
        csv_file = StringIO(text)
        reader = csv.DictReader(csv_file)

        submissions: list[RawSubmission] = []
        for row in reader:
            sid = row.get(self.config.student_id_column)
            if not sid:
                raise ValueError(
                    f"Student ID column '{self.config.student_id_column}' "
                    "not found in CSV row: {row}"
                )
            if self.config.answer_columns is None:
                non_answer_cols = {self.config.student_id_column}
                if self.config.point_columns:
                    non_answer_cols.update(self.config.point_columns.values())
                answers = {
                    k: (v if v is not None else "")
                    for k, v in row.items()
                    if k not in non_answer_cols
                }
            else:
                answers = {
                    col: str(row.get(col, "")) for col in self.config.answer_columns if col in row
                }

            pre_points: dict[str, QuestionResult] = {}
            if self.config.point_columns:
                for question_id, col in self.config.point_columns.items():
                    raw_val = row.get(col, "").strip()
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


raw_submissions_adapter_registry.register("csv", CsvRawSubmissionsAdapter)
