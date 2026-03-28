import csv
from io import StringIO

from gradeflow_engine.core import dump_submissions_to_blob
from gradeflow_engine.submissions.models import Submission


def _parse_csv(data: str) -> tuple[list[dict[str, str]], list[str]]:
    reader = csv.DictReader(StringIO(data))
    rows: list[dict[str, str]] = list(reader)
    headers: list[str] = list(reader.fieldnames or [])
    return rows, headers


def test_csv_serializer_headers_and_values(
    graded_submissions_sample: list[Submission],
) -> None:
    subs: list[Submission] = graded_submissions_sample
    blob = dump_submissions_to_blob(subs, serializer_name="csv")
    assert blob.extension == "csv"

    data: str = blob.data.decode("utf-8")
    rows, headers = _parse_csv(data)

    # Student column
    assert "student_id" in headers

    # Answer columns for union of QIDs (answers + results): expect Q1..Q6, QX
    for qid in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "QX"):
        assert qid in headers

    # Per-question result columns exist for every collected qid
    for qid in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "QX"):
        assert f"{qid}__points" in headers
        assert f"{qid}__max_points" in headers
        assert f"{qid}__passed" in headers
        assert f"{qid}__percent" in headers

    # Totals exist by default
    assert "total_points" in headers
    assert "total_max_points" in headers
    assert "total_percent" in headers

    # We supplied 4 graded submissions
    assert len(rows) == 4

    def by_id(sid: str) -> dict[str, str]:
        return next(r for r in rows if r.get("student_id") == sid)

    # s1 row assertions
    r1 = by_id("s1")
    # Choice set should be sorted and joined by "; "
    assert r1["Q2"] == "a; b"
    # Multi-valued list should be joined by " | "
    assert r1["Q3"] == "1 | two | None"
    # Numeric is stringified
    assert r1["Q4"] == "3.14"
    # Totals numeric strings; s1 points 1.0 + 0.0; max 1.0 + 2.0
    assert r1["total_points"] == "1.0"
    assert r1["total_max_points"] == "3.0"
    assert r1["total_percent"] == "33.33333333333333"

    # s2 row assertions
    r2 = by_id("s2")
    # Empty string preserved
    assert r2["Q3"] == ""
    # Text with delimiters and unicode should be present as-is
    assert "alpha, beta; gamma | δ" in r2["Q5"]
    # There is a result for QX but no answer; answer cell should be blank
    assert r2["QX"] == ""

    # s3 row assertions
    r3 = by_id("s3")
    # Uppercase set should be sorted lexicographically
    assert r3["Q2"] == "A; B"
    # List with empty, spaced, and zero
    assert r3["Q3"] == " |  spaced  | 0"

    # s4 row assertions
    r4 = by_id("s4")
    # Explicit None answer stringified as "None"
    assert r4["Q6"] == "None"
    # Zero max_points should produce N/A percent for that question
    assert r4["Q6__percent"] == "N/A"
