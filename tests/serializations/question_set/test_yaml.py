import pytest
import yaml

from gradeflow_engine.core import dump_question_set_to_blob, load_question_set_from_blob
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models.text import TextQuestion
from gradeflow_engine.serializations.base import DataBlob


def test_valid_minimal_parses() -> None:
    yaml_str = """
    question_map:
      q1:
        type: TEXT
        description: A simple text question
    """
    blob = DataBlob(
        data=yaml_str.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    qset = load_question_set_from_blob(blob, serializer_name="yaml")
    assert isinstance(qset, QuestionSet)
    assert "q1" in qset.question_map
    assert isinstance(qset.question_map["q1"], TextQuestion)
    assert getattr(qset.question_map["q1"], "type", None) == "TEXT"


def test_malformed_yaml_raises() -> None:
    bad_yaml = "question_map: [unbalanced"
    blob = DataBlob(
        data=bad_yaml.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    with pytest.raises(yaml.YAMLError):
        load_question_set_from_blob(blob, serializer_name="yaml")


def test_roundtrip_equal() -> None:
    # Build a minimal QuestionSet in code and round-trip via YAML
    qset = QuestionSet(question_map={"Q1": TextQuestion(description="free text")})
    out_blob = dump_question_set_to_blob(qset, serializer_name="yaml")
    assert out_blob.extension == "yaml"
    assert out_blob.media_type == "application/yaml"

    qset2 = load_question_set_from_blob(out_blob, serializer_name="yaml")
    assert qset2.model_dump() == qset.model_dump()
