import pytest
import yaml

from gradeflow_engine.core import dump_rubric_to_blob, load_rubric_from_blob
from gradeflow_engine.exceptions import DumpError, LoadError, RubricValidationError
from gradeflow_engine.rubrics.model import Rubric
from gradeflow_engine.rules.models.length import LengthQuestionRule
from gradeflow_engine.serializations.base import DataBlob
from gradeflow_engine.serializations.rubric import yaml as rubric_yaml


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
    assert len(rubric.rules[0].id) == 32


def test_malformed_yaml_raises_load_error() -> None:
    bad_yaml = "title: Bad:\n  - unbalanced"
    blob = DataBlob(
        data=bad_yaml.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    with pytest.raises(LoadError) as exc_info:
        load_rubric_from_blob(blob, serializer_name="yaml")
    assert exc_info.value.serializer == "yaml"


def test_missing_required_fields_raises_rubric_validation_error() -> None:
    missing_yaml = "something: 123"
    blob = DataBlob(
        data=missing_yaml.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    with pytest.raises(RubricValidationError) as exc_info:
        load_rubric_from_blob(blob, serializer_name="yaml")
    assert exc_info.value.validation_error is not None
    assert exc_info.value.title == "Rubric"
    errors = exc_info.value.errors()
    assert isinstance(errors, list)
    assert len(errors) > 0
    # Check that the error indicates missing 'rules' field
    assert any(
        error.get("loc") == ("rules",) and error.get("type") == "missing" for error in errors
    )


def test_non_strict_load_skips_invalid_rules() -> None:
    yaml_str = """
    rules:
      - id: valid-q1
        type: TEXT_MATCH
        question_id: q1
        answers:
          - Alice
      - id: broken-q2
        type: LENGTH
        question_id: q2
        min_length: not-a-number
    """
    blob = DataBlob(
        data=yaml_str.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )

    with pytest.raises(RubricValidationError):
        load_rubric_from_blob(blob, serializer_name="yaml")

    rubric = load_rubric_from_blob(blob, serializer_name="yaml", strict=False)

    assert [rule.id for rule in rubric.rules] == ["valid-q1"]


def test_dump_roundtrip_strips_engine_fields() -> None:
    rubric = Rubric(rules=[LengthQuestionRule(question_id="q1", min_length=1)])

    blob = dump_rubric_to_blob(rubric, serializer_name="yaml")
    text = blob.data.decode("utf-8")

    assert "question_types" not in text
    assert "constraints" not in text
    assert "id:" in text

    restored = load_rubric_from_blob(blob, serializer_name="yaml")
    assert restored.model_dump() == rubric.model_dump()


def test_rubric_yaml_dump_error_edge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rubric_yaml.yaml,
        "safe_dump",
        lambda obj, sort_keys=False: (_ for _ in ()).throw(yaml.YAMLError("bad dump")),
    )
    with pytest.raises(DumpError):
        rubric_yaml.YamlRubricSerializer().dumps(Rubric(rules=[]))
