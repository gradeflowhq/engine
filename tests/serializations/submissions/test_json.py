import json
from typing import Any

from gradeflow_engine.core import dump_submissions_to_blob
from gradeflow_engine.submissions.models import Submission


def test_json_serializer_compact_and_parseable(
    graded_submissions_sample: list[Submission],
) -> None:
    subs: list[Submission] = graded_submissions_sample
    blob = dump_submissions_to_blob(subs, serializer_name="json")
    assert blob.extension == "json"

    data: str = blob.data.decode("utf-8")
    payload: list[dict[str, Any]] = json.loads(data)
    assert isinstance(payload, list)
    assert len(payload) == 4

    item1: dict[str, Any] = next(i for i in payload if i.get("student_id") == "s1")
    assert "answer_map" in item1 and "result_map" in item1

    # sets serialized as sorted lists
    q2 = item1["answer_map"]["Q2"]
    assert isinstance(q2, list)
    assert set(q2) == {"a", "b"}
    # lists preserved with native types
    assert item1["answer_map"]["Q3"] == [1, "two", None]

    # result_map entries have required keys
    res: dict[str, Any] = next(iter(item1["result_map"].values()))
    assert {"passed", "points", "max_points", "feedback", "rule"}.issubset(res.keys())

    item3: dict[str, Any] = next(i for i in payload if i.get("student_id") == "s3")
    assert set(item3["answer_map"]["Q2"]) == {"A", "B"}
    assert item3["answer_map"]["Q3"] == ["", " spaced ", 0]
