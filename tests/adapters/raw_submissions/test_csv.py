import pytest

from gradeflow_engine.core import load_raw_submissions_via_adapter
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


def test_csv_adapter_missing_student_id_row_skipped() -> None:
    csv_text: str = "student_id,ans\n,empty\ns1,ok\n"
    with pytest.raises(ValueError):
        load_raw_submissions_via_adapter(
            StringSource(csv_text, media_type="text/csv", extension="csv"),
            adapter_name="csv",
        )


def test_csv_adapter_preserves_empty_strings_and_none_as_empty() -> None:
    # DictReader gives None for missing cells; adapter should map None -> ""
    csv_text: str = "student_id,a,b\ns1,,val\ns2,val2,\n"
    subs: list[RawSubmission] = load_raw_submissions_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="csv",
    )
    assert len(subs) == 2
    assert subs[0].raw_answer_map == {"a": "", "b": "val"}
    assert subs[1].raw_answer_map == {"a": "val2", "b": ""}
