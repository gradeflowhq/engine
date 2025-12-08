import pydantic
import pytest
import yaml

from gradeflow_engine.core import load_rubric_from_blob
from gradeflow_engine.rubrics.model import Rubric
from gradeflow_engine.rules.models.length import LengthQuestionRule
from gradeflow_engine.serializations.base import DataBlob


def test_valid_minimal_parses() -> None:
    yaml_str = """
    rules:
      - type: LENGTH
        question_id: q1
        min_length: 1
        max_points: 2.0
    """
    blob = DataBlob(
        data=yaml_str.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    rubric = load_rubric_from_blob(blob, serializer_name="yaml")
    assert isinstance(rubric, Rubric)
    assert len(rubric.rules) == 1
    assert isinstance(rubric.rules[0], LengthQuestionRule)
    assert rubric.rules[0].question_id == "q1"


def test_malformed_yaml_raises() -> None:
    bad_yaml = "title: Bad:\n  - unbalanced"
    blob = DataBlob(
        data=bad_yaml.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    with pytest.raises(yaml.YAMLError):
        load_rubric_from_blob(blob, serializer_name="yaml")


def test_missing_required_fields_raises() -> None:
    missing_yaml = "something: 123"
    blob = DataBlob(
        data=missing_yaml.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    with pytest.raises(pydantic.ValidationError):
        load_rubric_from_blob(blob, serializer_name="yaml")
