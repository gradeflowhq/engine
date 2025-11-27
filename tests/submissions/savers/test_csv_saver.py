import csv
from io import StringIO

from gradeflow_engine.rules.result import QuestionResult
from gradeflow_engine.submissions.models import GradedSubmission
from gradeflow_engine.submissions.savers.csv_saver import CsvSubmissionsSaver


def _make_graded_submissions() -> list[GradedSubmission]:
    gs1 = GradedSubmission(
        student_id="s1",
        answer_map={"Q1": "hello", "Q2": {"b", "a"}, "Q3": [1, "two"]},
        results=[
            QuestionResult(
                question_id="Q1",
                output=True,
                passed=True,
                feedback="ok",
                rule="ExactMatchQuestionRule",
                points=1.0,
                max_points=1.0,
            ),
            QuestionResult(
                question_id="Q2",
                output=False,
                passed=False,
                feedback="miss",
                rule="MultipleChoiceQuestionRule",
                points=0.0,
                max_points=2.0,
            ),
        ],
    )
    gs2 = GradedSubmission(
        student_id="s2",
        answer_map={"Q1": "world"},
        results=[
            QuestionResult(
                question_id="Q1",
                output=False,
                passed=False,
                feedback="not ok",
                rule="ExactMatchQuestionRule",
                points=0.0,
                max_points=1.0,
            )
        ],
    )
    return [gs1, gs2]


def test_csv_saver_default_columns_and_serialization() -> None:
    submissions = _make_graded_submissions()
    saver = CsvSubmissionsSaver()  # defaults: include answers, per-question results, totals
    out = saver.save(submissions)

    assert out.extension == "csv"
    assert isinstance(out.data, str)

    # Parse CSV to verify headers and data
    buf = StringIO(out.data)
    reader = csv.DictReader(buf)
    headers = reader.fieldnames or []

    # Default student_id column
    assert "student_id" in headers

    # Answers columns for union of question IDs (Q1, Q2, Q3)
    for qid in ("Q1", "Q2", "Q3"):
        assert qid in headers

    # Per-question results columns exist
    for qid in ("Q1", "Q2", "Q3"):
        assert f"{qid}__points" in headers
        assert f"{qid}__max_points" in headers
        assert f"{qid}__passed" in headers

    # Totals exist
    assert "total_points" in headers
    assert "total_max_points" in headers

    # Check serialization specifics:
    rows = list(reader)
    assert len(rows) == 2

    r1 = rows[0]
    # Choice set should be sorted and joined with "; "
    # We provided {"b","a"} -> "a; b"
    assert r1["Q2"] in {"a; b", "b; a"}  # tolerate potential order; implementation sorts
    assert r1["Q2"] == "a; b"

    # Multi-valued list should be joined by " | "
    assert r1["Q3"] == "1 | two"

    # Totals are numeric strings; for s1 points 1.0 + 0.0 = 1.0; max 1.0 + 2.0 = 3.0
    assert r1["total_points"] == "1.0"
    assert r1["total_max_points"] == "3.0"

    r2 = rows[1]
    # s2 only answered Q1; other columns should be present but can be empty
    assert r2["Q1"] == "world"
    assert r2["Q2"] == ""  # no answer
    assert r2["Q3"] == ""  # no answer
    # totals: only one result with 0 points, 1 max
    assert r2["total_points"] == "0.0"
    assert r2["total_max_points"] == "1.0"


def test_csv_saver_custom_student_id_column() -> None:
    submissions = _make_graded_submissions()
    saver = CsvSubmissionsSaver(student_id_column="id", include_total=False)
    out = saver.save(submissions)

    buf = StringIO(out.data)
    reader = csv.DictReader(buf)
    headers = reader.fieldnames or []
    assert "id" in headers
    assert "student_id" not in headers
    assert "total_points" not in headers
    assert "total_max_points" not in headers
