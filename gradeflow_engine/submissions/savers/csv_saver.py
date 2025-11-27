import csv
from collections.abc import Iterable
from io import StringIO
from typing import Literal

from natsort import natsorted

from ...questions.types import Answer
from ...registry import submissions_saver_registry
from ..models import GradedSubmission
from .base import BaseSubmissionsSaver, SubmissionsSaverOutput


def _serialize_answer(answer: Answer) -> str:
    """
    Convert an Answer into a deterministic, human-readable string.
    - set[str] (e.g., CHOICE answers): sorted and joined by '; '
    - list[...] (e.g., MULTI_VALUED answers): stringified items joined by ' | '
    - numeric/text: str()
    """
    if isinstance(answer, set):
        # ChoiceAnswer: stable ordering
        return "; ".join(sorted(map(str, answer)))
    if isinstance(answer, list):
        return " | ".join(map(str, answer))
    return str(answer)


def save_graded_submissions(
    submissions: Iterable[GradedSubmission],
    *,
    student_id_column: str = "student_id",
    include_answers: bool = True,
    include_per_question_results: bool = True,
    include_total: bool = True,
) -> str:
    """
    Export graded submissions to CSV.

    Columns:
      - student_id_column
      - If include_answers: one column per question ID with serialized answers
      - If include_per_question_results: for each question ID, three columns:
          <qid>__points, <qid>__max_points, <qid>__passed
      - If include_total: total_points, total_max_points

    Notes:
      - If a question has an answer but no result (or vice versa), blanks are emitted where missing.
      - Question IDs are collected from both answer_map and results to ensure complete coverage.
    """
    submissions = list(submissions)

    # Collect union of question IDs from answers and results
    question_ids: set[str] = set()
    for gs in submissions:
        question_ids.update(gs.answer_map.keys())
        question_ids.update(res.question_id for res in gs.results)
    ordered_qids = natsorted(question_ids)

    fieldnames: list[str] = [student_id_column]

    if include_answers:
        fieldnames += ordered_qids

    if include_per_question_results:
        for qid in ordered_qids:
            fieldnames += [f"{qid}__points", f"{qid}__max_points", f"{qid}__passed"]

    if include_total:
        fieldnames += ["total_points", "total_max_points"]

    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for gs in submissions:
        row: dict[str, str] = {student_id_column: gs.student_id}

        # Answers
        if include_answers:
            for qid in ordered_qids:
                ans = gs.answer_map.get(qid, "")
                row[qid] = _serialize_answer(ans)

        # Build quick lookup for results per question
        result_by_qid = {res.question_id: res for res in gs.results}

        # Per-question results
        if include_per_question_results:
            for qid in ordered_qids:
                res = result_by_qid.get(qid)
                row[f"{qid}__points"] = "" if res is None else str(res.points)
                row[f"{qid}__max_points"] = "" if res is None else str(res.max_points)
                row[f"{qid}__passed"] = "" if res is None else ("TRUE" if res.passed else "FALSE")

        # Totals
        if include_total:
            total_points = sum(res.points for res in gs.results)
            total_max_points = sum(res.max_points for res in gs.results)
            row["total_points"] = str(total_points)
            row["total_max_points"] = str(total_max_points)

        writer.writerow(row)

    return out.getvalue()


@submissions_saver_registry.register_decorator("CSV")
class CsvSubmissionsSaver(BaseSubmissionsSaver):
    name: Literal["CSV"] = "CSV"
    student_id_column: str = "student_id"
    include_answers: bool = True
    include_per_question_results: bool = True
    include_total: bool = True

    def save(self, submissions: Iterable[GradedSubmission]) -> SubmissionsSaverOutput:
        return SubmissionsSaverOutput(
            data=save_graded_submissions(
                submissions,
                student_id_column=self.student_id_column,
                include_answers=self.include_answers,
                include_per_question_results=self.include_per_question_results,
                include_total=self.include_total,
            ),
            extension="csv",
        )
