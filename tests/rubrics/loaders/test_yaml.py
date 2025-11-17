import pytest
import yaml
from pydantic import ValidationError

from gradeflow_engine.rubrics.loaders.yaml import load_rubric
from gradeflow_engine.rubrics.model import Rubric
from gradeflow_engine.rules.models.length import LengthQuestionRule


def test_import_rubric_valid_minimal():
    """A minimal valid YAML should parse into a Rubric instance."""
    yaml_str = """
rules:
  - type: LENGTH
    question_id: q1
    min_length: 1
    max_points: 2.0
"""

    rubric = load_rubric(yaml_str)
    assert isinstance(rubric, Rubric)
    # Rubric should have one rule and it should target question_id 'q1'
    assert len(rubric.rules) == 1
    rule = rubric.rules[0]
    assert isinstance(rule, LengthQuestionRule)
    assert getattr(rule, "question_id", None) == "q1"
    assert getattr(rule, "min_length", None) == 1


def test_import_rubric_invalid_yaml_raises():
    """Malformed YAML should raise a YAML error or validation error."""
    bad_yaml = "title: Bad:\n  - unbalanced"

    with pytest.raises(yaml.YAMLError):
        load_rubric(bad_yaml)


def test_import_rubric_missing_required_fields_raises():
    """YAML missing required fields should raise a validation error from the Rubric model."""
    missing_yaml = """
    # no title and no criteria
    something: 123
    """

    with pytest.raises(ValidationError):
        load_rubric(missing_yaml)
