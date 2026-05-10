import pytest
import yaml

from gradeflow_engine.core import dump_question_set_to_blob, load_question_set_from_blob
from gradeflow_engine.exceptions import DumpError, LoadError, QuestionSetValidationError
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models.text import TextQuestion
from gradeflow_engine.serializations.base import DataBlob
from gradeflow_engine.serializations.question_set import yaml as qset_yaml


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


def test_malformed_yaml_raises_load_error() -> None:
    bad_yaml = "question_map: [unbalanced"
    blob = DataBlob(
        data=bad_yaml.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    with pytest.raises(LoadError) as exc_info:
        load_question_set_from_blob(blob, serializer_name="yaml")
    assert exc_info.value.serializer == "yaml"


def test_roundtrip_equal() -> None:
    # Build a minimal QuestionSet in code and round-trip via YAML
    qset = QuestionSet(question_map={"Q1": TextQuestion(description="free text")})
    out_blob = dump_question_set_to_blob(qset, serializer_name="yaml")
    assert out_blob.extension == "yaml"
    assert out_blob.media_type == "application/yaml"

    qset2 = load_question_set_from_blob(out_blob, serializer_name="yaml")
    assert qset2.model_dump() == qset.model_dump()


def test_non_strict_question_set_load_is_not_supported() -> None:
    with pytest.raises(NotImplementedError):
        qset_yaml.YamlQuestionSetSerializer().loads(
            DataBlob(data=b"question_map: {}", media_type="application/yaml", extension="yaml"),
            strict=False,
        )


def test_question_set_yaml_error_and_validation_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        qset_yaml.yaml,
        "safe_dump",
        lambda obj: (_ for _ in ()).throw(yaml.YAMLError("bad dump")),
    )
    with pytest.raises(DumpError):
        qset_yaml.YamlQuestionSetSerializer().dumps(QuestionSet(question_map={}))

    with pytest.raises(QuestionSetValidationError):
        qset_yaml.YamlQuestionSetSerializer().loads(
            DataBlob(data=b"question_map: []", media_type="application/yaml", extension="yaml")
        )
