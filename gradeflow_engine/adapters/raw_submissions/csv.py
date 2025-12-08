import csv
from io import StringIO
from typing import Literal

from pydantic import BaseModel, Field

from ...io.sources import DataSource
from ...submissions.models import RawSubmission
from ..registries import RawSubmissionsAdapter, raw_submissions_adapter_registry


class CsvRawSubmissionsConfig(BaseModel):
    name: Literal["csv"] = "csv"
    format: Literal["csv"] = "csv"
    student_id_column: str = Field(default="student_id")
    answer_columns: list[str] | None = Field(default=None)


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
                answers = {
                    k: (v if v is not None else "")
                    for k, v in row.items()
                    if k != self.config.student_id_column
                }
            else:
                answers = {
                    col: str(row.get(col, "")) for col in self.config.answer_columns if col in row
                }
            submissions.append(RawSubmission(student_id=sid, raw_answer_map=answers))
        return submissions


raw_submissions_adapter_registry.register("csv", CsvRawSubmissionsAdapter)
