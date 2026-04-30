from typing import Any, cast

from gradeflow_engine.rubrics.model import Rubric
from gradeflow_engine.serializations.rubric.utils import model_dump_minimal


def test_model_dump_minimal_strips_engine_fields_from_models() -> None:
    rubric = Rubric.model_validate(
        {
            "rules": [
                {
                    "type": "LENGTH",
                    "question_id": "q1",
                    "min_length": 1,
                }
            ]
        }
    )

    dumped = model_dump_minimal(rubric)

    assert isinstance(dumped, dict)
    rules = cast(list[dict[str, Any]], dumped["rules"])
    rule = rules[0]
    assert "question_types" not in rule
    assert "constraints" not in rule
    assert "min_length" in rule
    assert rule["min_length"] == 1
    assert "question_id" in rule
    assert rule["question_id"] == "q1"
    assert rule["type"] == "LENGTH"


def test_model_dump_minimal_strips_engine_fields_from_nested_models() -> None:
    rubric = Rubric.model_validate(
        {
            "rules": [
                {
                    "type": "COMPOSITE",
                    "question_id": "q1",
                    "aggregation": "ALL",
                    "rules": [
                        {
                            "type": "MULTIPLE_CHOICE",
                            "answer": ["A"],
                            "mode": "ALL",
                        },
                    ],
                }
            ]
        }
    )

    dumped = model_dump_minimal(rubric)

    assert isinstance(dumped, dict)
    rules = cast(list[dict[str, Any]], dumped["rules"])
    outer_rule = rules[0]
    inner_rule = cast(list[dict[str, Any]], outer_rule["rules"])[0]
    assert "question_types" not in outer_rule
    assert "constraints" not in outer_rule
    assert "question_types" not in inner_rule
    assert "constraints" not in inner_rule
    assert outer_rule["type"] == "COMPOSITE"
    assert outer_rule["question_id"] == "q1"
    assert outer_rule["aggregation"] == "ALL"
    assert inner_rule["type"] == "MULTIPLE_CHOICE"
    assert inner_rule["answer"] == {"A"}
    assert inner_rule["mode"] == "ALL"
