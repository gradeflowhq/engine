import logging

from pytest import LogCaptureFixture

from gradeflow_engine.submissions.loaders.csv import load_submissions
from gradeflow_engine.submissions.models import RawSubmission


def test_basic_import() -> None:
    csv_data = """student_id,q1,q2
s1,foo,bar
s2,baz,qux
"""

    submissions = load_submissions(csv_data)

    assert len(submissions) == 2
    assert all(isinstance(s, RawSubmission) for s in submissions)

    s1, s2 = submissions
    assert s1.student_id == "s1"
    assert s1.raw_answer_map == {"q1": "foo", "q2": "bar"}

    assert s2.student_id == "s2"
    assert s2.raw_answer_map == {"q1": "baz", "q2": "qux"}


def test_custom_student_id_column() -> None:
    csv_data = """id,answer
123,yes
"""

    submissions = load_submissions(csv_data, student_id_column="id")

    assert len(submissions) == 1
    assert all(isinstance(s, RawSubmission) for s in submissions)
    submission = submissions[0]
    assert submission.student_id == "123"
    assert submission.raw_answer_map == {"answer": "yes"}


def test_answer_columns_filtering() -> None:
    csv_data = """student_id,q1,q2
s1,1,2
"""

    submissions = load_submissions(csv_data, answer_columns=["q1", "missing"])

    assert len(submissions) == 1
    assert all(isinstance(s, RawSubmission) for s in submissions)
    submission = submissions[0]
    # only q1 should be present, missing is ignored
    assert submission.raw_answer_map == {"q1": "1"}


def test_skip_missing_student_id_logs_warning(caplog: LogCaptureFixture) -> None:
    csv_data = """student_id,q1
,empty
s1,ok
"""

    caplog.set_level(logging.WARNING)
    submissions = load_submissions(csv_data)

    # only one valid submission
    assert len(submissions) == 1
    assert submissions[0].student_id == "s1"

    # ensure a warning was emitted about the missing student id
    msgs = [r.message for r in caplog.records]
    assert any("Row missing student ID" in m for m in msgs)
