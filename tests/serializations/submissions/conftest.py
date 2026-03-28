import pytest

from gradeflow_engine.rules.result import QuestionResult
from gradeflow_engine.submissions.models import Submission


@pytest.fixture
def graded_submissions_sample() -> list[Submission]:
    """
    A comprehensive set of graded submissions to exercise serializer edge cases:
    - Mixed answer types: text, numeric, choice set, multi-valued list, None
    - Answers containing delimiters, whitespace, unicode
    - Results covering pass/fail, fractional points, zero max_points (percent N/A), and
      question IDs not present in answer_map (to ensure header union and blanks)
    """
    return [
        # s1: typical mixture
        Submission(
            student_id="s1",
            answer_map={
                "Q1": "hello",
                "Q2": {"b", "a"},  # choice set -> CSV should sort "a; b"
                "Q3": [1, "two", None],  # multi-valued list -> CSV "1 | two | None"
                "Q4": 3.14,  # numeric
            },
            result_map={
                "Q1": QuestionResult(
                    output=True,
                    passed=True,
                    feedback="exact match",
                    rule="TextMatchQuestionRule",
                    points=1.0,
                    max_points=1.0,
                ),
                "Q2": QuestionResult(
                    output=False,
                    passed=False,
                    feedback="incorrect choices",
                    rule="MultipleChoiceQuestionRule",
                    points=0.0,
                    max_points=2.0,
                ),
            },
        ),
        # s2: delimiters and unicode, missing some answers
        Submission(
            student_id="s2",
            answer_map={
                "Q1": "world",
                "Q3": "",  # empty string
                # text containing commas, semicolons, pipes, and unicode
                "Q5": "alpha, beta; gamma | δ",
            },
            result_map={
                "Q1": QuestionResult(
                    output=False,
                    passed=False,
                    feedback="no match",
                    rule="TextMatchQuestionRule",
                    points=0.0,
                    max_points=1.0,
                ),
                # Result for a question not present in answers to test header union and blank cells
                "QX": QuestionResult(
                    output=True,
                    passed=True,
                    feedback="bonus",
                    rule="BonusQuestionRule",
                    points=0.5,
                    max_points=0.5,
                ),
            },
        ),
        # s3: additional choice and multi-valued coverage, different ordering
        Submission(
            student_id="s3",
            answer_map={
                "Q2": {"B", "A"},  # case difference; serializers just stringify
                "Q3": ["", " spaced ", 0],  # list with empty string, whitespace, numeric 0
            },
            result_map={
                # Include a result with fractional points
                "Q2": QuestionResult(
                    output=0.5,
                    passed=True,
                    feedback="partial credit",
                    rule="MultipleChoiceQuestionRule",
                    points=1.5,
                    max_points=3.0,
                ),
            },
        ),
        # s4: None answers and zero max points (percent should be N/A)
        Submission(
            student_id="s4",
            answer_map={
                "Q6": None,  # explicit None
            },
            result_map={
                "Q6": QuestionResult(
                    output=False,
                    passed=False,
                    feedback="ungraded/zero max",
                    rule="ManualQuestionRule",
                    points=0.0,
                    max_points=0.0,  # triggers N/A percent in CSV
                ),
            },
        ),
    ]
