import pytest

from gradeflow_engine.adapters.raw_submissions.csv import ORIGINAL_POINTS_RULE_NAME
from gradeflow_engine.core import load_raw_submissions_via_adapter
from gradeflow_engine.exceptions import MalformedCsvRowError, MissingStudentIdError
from gradeflow_engine.io.sources import StringSource
from gradeflow_engine.submissions.models import RawSubmission


def test_csv_adapter_basic_via_core() -> None:
    csv_text: str = "student_id,q1,q2\ns1,foo,bar\ns2,baz,qux\n"
    subs: list[RawSubmission] = load_raw_submissions_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="csv",
    )
    assert len(subs) == 2
    assert subs[0].student_id == "s1"
    assert subs[0].raw_answer_map == {"q1": "foo", "q2": "bar"}
    assert subs[1].raw_answer_map == {"q1": "baz", "q2": "qux"}


def test_csv_adapter_custom_student_id_and_answer_filter_direct() -> None:
    # Use public core API with adapter kwargs
    csv_text: str = "id,a,b,extra\n123,x,y,z\n456,m,n,o\n"
    subs: list[RawSubmission] = load_raw_submissions_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="csv",
        adapter_kwargs={
            "student_id_column": "id",
            "answer_columns": ["a", "b"],  # filter to specific columns
        },
    )
    assert len(subs) == 2
    assert subs[0].student_id == "123"
    assert subs[0].raw_answer_map == {"a": "x", "b": "y"}
    assert subs[1].raw_answer_map == {"a": "m", "b": "n"}


def test_csv_adapter_missing_student_id_raises() -> None:
    csv_text: str = "student_id,ans\n,empty\ns1,ok\n"
    with pytest.raises(MissingStudentIdError) as exc_info:
        load_raw_submissions_via_adapter(
            StringSource(csv_text, media_type="text/csv", extension="csv"),
            adapter_name="csv",
        )
    assert exc_info.value.column == "student_id"


def test_csv_adapter_malformed_row_reports_csv_line_number() -> None:
    csv_text: str = "student_id,q1,q2\ns1,answer\n"
    with pytest.raises(MalformedCsvRowError) as exc_info:
        load_raw_submissions_via_adapter(
            StringSource(csv_text, media_type="text/csv", extension="csv"),
            adapter_name="csv",
        )

    assert exc_info.value.line_number == 2
    assert str(exc_info.value).startswith("CSV row 2 is malformed.")


def test_csv_adapter_preserves_empty_strings() -> None:
    csv_text: str = "student_id,a,b\ns1,,val\ns2,val2,\n"
    subs: list[RawSubmission] = load_raw_submissions_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="csv",
    )
    assert len(subs) == 2
    assert subs[0].raw_answer_map == {"a": "", "b": "val"}
    assert subs[1].raw_answer_map == {"a": "val2", "b": ""}


def test_csv_adapter_point_columns_populate_result_map() -> None:
    csv_text: str = "student_id,q1,q2,score_q1\ns1,yes,no,3.5\ns2,no,yes,0.0\n"
    subs: list[RawSubmission] = load_raw_submissions_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="csv",
        adapter_kwargs={"point_columns": {"q1": "score_q1"}},
    )
    assert len(subs) == 2

    # score_q1 column should not appear in raw_answer_map
    assert "score_q1" not in subs[0].raw_answer_map
    assert "score_q1" not in subs[1].raw_answer_map

    # s1: 3.5 points pre-populated
    r1 = subs[0].result_map["q1"]
    assert r1.points == 3.5
    assert r1.max_points == 3.5
    assert r1.passed is True
    assert r1.rule == ORIGINAL_POINTS_RULE_NAME

    # s2: 0.0 — stored with passed=False
    r2 = subs[1].result_map["q1"]
    assert r2.points == 0.0
    assert r2.passed is False
    assert r2.rule == ORIGINAL_POINTS_RULE_NAME


def test_csv_adapter_point_columns_excluded_from_answers_with_explicit_answer_columns() -> None:
    # When answer_columns is set explicitly, point columns are irrelevant to filtering
    csv_text: str = "student_id,q1,q2,pts\ns1,ans1,ans2,2.0\n"
    subs: list[RawSubmission] = load_raw_submissions_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="csv",
        adapter_kwargs={"answer_columns": ["q1", "q2"], "point_columns": {"q1": "pts"}},
    )
    assert subs[0].raw_answer_map == {"q1": "ans1", "q2": "ans2"}
    assert subs[0].result_map["q1"].points == 2.0


def test_csv_adapter_point_columns_invalid_value_defaults_to_zero() -> None:
    csv_text: str = "student_id,q1,pts\ns1,ans,notanumber\n"
    subs: list[RawSubmission] = load_raw_submissions_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="csv",
        adapter_kwargs={"point_columns": {"q1": "pts"}},
    )
    r = subs[0].result_map["q1"]
    assert r.points == 0.0
    assert r.passed is False
