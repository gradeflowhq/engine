"""
Tests for RegexRule grading logic.
"""

import pytest

from gradeflow_engine import RegexRule, Rubric, Submission, grade
from gradeflow_engine.rules.regex.model import RegexRuleConfig
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestRegexRule:
    """Test RegexRule grading logic."""

    def test_pattern_matches(self):
        """A single pattern that matches should award max_points."""
        rule = RegexRule(question_id="q1", pattern=r"\d+", max_points=5.0)
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "ABC 123"})])
        assert result.results[0].total_points == 5.0

    def test_pattern_does_not_match(self):
        """A pattern that does not match should award zero points."""
        rule = RegexRule(question_id="q1", pattern=r"[A-Z]", max_points=5.0)
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "123"})])
        assert result.results[0].total_points == 0.0

    def test_case_insensitive(self):
        """Case-insensitive matching via config.ignore_case should match."""
        rule = RegexRule(
            question_id="q1",
            pattern=r"python",
            max_points=10.0,
            config=RegexRuleConfig(ignore_case=True),
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "I love PYTHON"})])
        assert result.results[0].total_points == 10.0

    def test_multiline_and_dotall(self):
        """multi_line and dotall flags in config allow matching across lines."""
        rule = RegexRule(
            question_id="q1",
            pattern=r"^Start.*End$",
            max_points=10.0,
            config=RegexRuleConfig(multi_line=True, dotall=True),
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric,
            [Submission(student_id="s1", answers={"q1": "Start\nmiddle\nEnd"})],
        )
        assert result.results[0].total_points == 10.0

    def test_invalid_pattern_raises_on_model_creation(self):
        """Invalid regex patterns should raise during model validation."""
        with pytest.raises(ValueError):
            RegexRule(question_id="q1", pattern="(", max_points=1.0)


class TestRegexSchemaValidation:
    """Test RegexRule schema validation."""

    def test_validate_against_text_schema(self):
        """RegexRule validates correctly against TEXT schema."""
        rule = RegexRule(question_id="q1", pattern=r"\d+", max_points=10.0)
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": TextQuestionSchema(),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert errors == []

    def test_validate_incompatible_choice_schema(self):
        """RegexRule rejects CHOICE schema."""
        rule = RegexRule(question_id="q1", pattern=r"[A-Z]", max_points=10.0)
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(options=["A", "B", "C"]),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "CHOICE" in errors[0]

    def test_validate_incompatible_numeric_schema(self):
        """RegexRule rejects NUMERIC schema."""
        rule = RegexRule(question_id="q1", pattern=r"\d+", max_points=10.0)
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": NumericQuestionSchema(),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "NUMERIC" in errors[0]
