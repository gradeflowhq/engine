from . import question_set as question_set
from . import raw_submissions as raw_submissions
from . import rubric as rubric
from .question_set.examplify import ExamplifyQuestionSetAdapter
from .raw_submissions.csv import CsvRawSubmissionsAdapter
from .registries import (
    question_set_adapter_registry,
    raw_submissions_adapter_registry,
    rubric_adapter_registry,
)
from .rubric.examplify import ExamplifyRubricAdapter


def register_builtins() -> None:
    question_set_adapter_registry.register("examplify", ExamplifyQuestionSetAdapter, overwrite=True)
    raw_submissions_adapter_registry.register("csv", CsvRawSubmissionsAdapter, overwrite=True)
    rubric_adapter_registry.register("examplify", ExamplifyRubricAdapter, overwrite=True)
