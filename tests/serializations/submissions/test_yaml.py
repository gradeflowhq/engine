from typing import Any

import yaml

from gradeflow_engine.core import dump_submissions_to_blob
from gradeflow_engine.submissions.models import Submission


def test_yaml_serializer_roundtrip_shape(
    graded_submissions_sample: list[Submission],
) -> None:
    subs: list[Submission] = graded_submissions_sample
    blob = dump_submissions_to_blob(subs, serializer_name="yaml")
    assert blob.extension == "yaml"

    data: str = blob.data.decode("utf-8")
    payload: list[dict[str, Any]] = yaml.safe_load(data)
    assert isinstance(payload, list)
    assert len(payload) == 4

    item1: dict[str, Any] = next(i for i in payload if i.get("student_id") == "s1")
    assert "answer_map" in item1 and "result_map" in item1

    amap1: dict[str, Any] = item1["answer_map"]
    # native types via model_dump
    assert amap1["Q1"] == "hello"
    assert isinstance(amap1["Q2"], set)
    assert set(amap1["Q2"]) == {"a", "b"}
    assert amap1["Q3"] == [1, "two", None]
    assert amap1["Q4"] == 3.14

    # zero max points record present
    item4: dict[str, Any] = next(i for i in payload if i.get("student_id") == "s4")
    res4: dict[str, Any] = item4["result_map"]["Q6"]
    assert res4["max_points"] == 0.0
    assert res4["points"] == 0.0
