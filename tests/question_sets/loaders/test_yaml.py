import pytest
import yaml
from pydantic import ValidationError

from gradeflow_engine.question_sets.loaders.yaml import load_question_set
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models.text import TextQuestion


def test_import_question_set_valid_minimal() -> None:
    """A minimal valid QuestionSet YAML should parse into a QuestionSet instance."""
    yaml_str = """
    question_map:
      q1:
        type: TEXT
        description: A simple text question
    """

    qset = load_question_set(yaml_str)
    assert qset is not None
    assert isinstance(qset, QuestionSet)
    assert hasattr(qset, "question_map")
    assert "q1" in qset.question_map
    q = qset.question_map["q1"]
    assert isinstance(q, TextQuestion)
    assert getattr(q, "type", None) == "TEXT"


def test_import_question_set_invalid_yaml_raises() -> None:
    bad_yaml = "question_map: [unbalanced"
    # malformed YAML should raise a YAML parse error
    with pytest.raises(yaml.YAMLError):
        load_question_set(bad_yaml)


def test_import_question_set_missing_required_fields_raises() -> None:
    # question_map missing or empty should raise validation error
    missing_yaml = """
    something: 1
    """
    # missing required fields should raise a pydantic validation error
    with pytest.raises(ValidationError):
        load_question_set(missing_yaml)
