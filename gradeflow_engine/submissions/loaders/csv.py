import csv
import logging
from io import StringIO
from typing import Literal

from ...registry import submissions_loader_registry
from ..models import RawSubmission
from .base import BaseSubmissionsLoader

logger = logging.getLogger(__name__)


def load_submissions(
    csv_data: str,
    student_id_column: str = "student_id",
    answer_columns: list[str] | None = None,
) -> list[RawSubmission]:
    """
    Imports submissions from a CSV string.

    Args:
        csv_data (str): The CSV data as a string.
        student_id_column (str): The column name for student IDs.
        answer_columns (list[str] | None): List of column names for answers.
            If None, all columns except student_id_column are used.

    Returns:
        list[RawSubmission]: A list of RawSubmission objects.
    """
    submissions: list[RawSubmission] = []
    csv_file = StringIO(csv_data)
    reader = csv.DictReader(csv_file)

    for row in reader:
        student_id = row.get(student_id_column)
        if not student_id:
            logger.warning(f"Row missing student ID in column '{student_id_column}': {row}")
            continue  # Skip rows without a valid student ID

        if answer_columns is None:
            answers = {
                k: (v if v is not None else "") for k, v in row.items() if k != student_id_column
            }
        else:
            answers = {col: str(row.get(col, "")) for col in answer_columns if col in row}

        submission = RawSubmission(student_id=student_id, raw_answer_map=answers)
        submissions.append(submission)

    return submissions


@submissions_loader_registry.register_decorator("CSV")
class CsvSubmissionsLoader(BaseSubmissionsLoader):
    name: Literal["CSV"] = "CSV"
    student_id_column: str = "student_id"
    answer_columns: list[str] | None = None

    def load(self, data: str) -> list[RawSubmission]:
        return load_submissions(
            data,
            student_id_column=self.student_id_column,
            answer_columns=self.answer_columns,
        )
