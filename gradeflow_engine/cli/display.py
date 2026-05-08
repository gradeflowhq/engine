from natsort import natsorted
from rich import box
from rich.table import Table

from ..question_sets.model import QuestionSet
from ..rubrics.model import RubricCoverage
from ..submissions.models import Submission
from . import console


def print_question_set(qset: QuestionSet, title: str = "Question Set") -> None:
    console.rule(title)
    table = Table(box=box.SIMPLE)
    table.add_column("Question ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta", no_wrap=True)
    for qid, question in qset.question_map.items():
        table.add_row(qid, question.type)  # type: ignore[attr-defined]
    console.print(table)


def print_submissions(submissions: list[Submission]) -> None:
    console.rule("Parsed Submissions")
    table = Table(box=box.SIMPLE)
    table.add_column("Student ID", style="green", no_wrap=True)
    table.add_column("# Answers", justify="right", no_wrap=True)
    for submission in submissions:
        table.add_row(submission.student_id, str(len(submission.answer_map)))
    console.print(table)


def print_validation_errors(errors: list[str]) -> None:
    if not errors:
        return
    console.rule("Rubric Validation Errors")
    table = Table(box=box.SIMPLE)
    table.add_column("Error", style="red")
    for error in errors:
        table.add_row(error)
    console.print(table)


def print_grades(submissions: list[Submission]) -> None:
    if not submissions:
        return
    console.rule("Graded Submissions")
    table = Table(box=box.SIMPLE)
    table.add_column("Student ID", style="green", no_wrap=True)
    table.add_column("Total Points", justify="right", no_wrap=True)
    table.add_column("Max Points", justify="right", no_wrap=True)
    for submission in submissions:
        total_points = sum(result.points for result in submission.result_map.values())
        total_max = sum(result.max_points for result in submission.result_map.values())
        table.add_row(submission.student_id, f"{total_points:.2f}", f"{total_max:.2f}")
    console.print(table)


def print_coverage(coverage: RubricCoverage) -> None:
    console.rule("Rubric Coverage")
    summary = Table(box=box.SIMPLE)
    summary.add_column("Total Questions", justify="right", no_wrap=True)
    summary.add_column("Covered by Rubric", justify="right", no_wrap=True)
    summary.add_column("Coverage", justify="right", no_wrap=True)
    summary.add_row(str(coverage.total), str(coverage.covered), f"{coverage.percentage:.0%}")
    console.print(summary)

    covered_ids = natsorted(coverage.covered_question_ids)
    uncovered_ids = natsorted(coverage.uncovered_question_ids)

    details = Table(box=box.SIMPLE)
    details.add_column("Covered IDs", style="green")
    details.add_column("Uncovered IDs", style="red")
    details.add_row(
        ", ".join(covered_ids) if covered_ids else "<none>",
        ", ".join(uncovered_ids) if uncovered_ids else "<none>",
    )
    console.print(details)
