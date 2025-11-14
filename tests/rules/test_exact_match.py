"""
Tests for ExactMatchRule grading logic.
"""

from gradeflow_engine import ExactMatchRule, Rubric, Submission, grade
from gradeflow_engine.rules.base import TextRuleConfig
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestExactMatchRule:
    """Test ExactMatchRule grading logic."""

    def test_case_insensitive_match(self):
        """Test case-insensitive exact matching."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="Paris",
            max_points=10.0,
            config=TextRuleConfig(ignore_case=True),
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Should match regardless of case
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "paris"})])
        assert result.results[0].total_points == 10.0
        assert result.results[0].grade_details[0].is_correct

        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "PARIS"})])
        assert result.results[0].total_points == 10.0

    def test_case_sensitive_match(self):
        """Test case-sensitive exact matching."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="Paris",
            max_points=10.0,
            config=TextRuleConfig(ignore_case=False),
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Exact case match
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 10.0

        # Wrong case
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "paris"})])
        assert result.results[0].total_points == 0.0

    def test_whitespace_trimming(self):
        """Test whitespace trimming."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="Paris",
            max_points=10.0,
            config=TextRuleConfig(trim_whitespace=True),
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "  Paris  "})])
        assert result.results[0].total_points == 10.0

    def test_unicode_in_answers(self):
        """Test Unicode characters in answers."""
        rule = ExactMatchRule(question_id="q1", answer="café", max_points=10.0)
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "café"})])
        assert result.results[0].total_points == 10.0

    def test_emoji_in_answers(self):
        """Test emoji in answers."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="Hello 👋",
            max_points=5.0,
            config=TextRuleConfig(ignore_case=True),
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "hello 👋"})])
        assert result.results[0].total_points == 5.0

    def test_internal_whitespace_preserved(self):
        """Test that internal whitespace is preserved."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="New York",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "New York"})])
        assert result.results[0].total_points == 10.0

    def test_tabs_and_newlines(self):
        """Test handling of tabs and newlines in trimming."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="Answer",
            max_points=10.0,
            config=TextRuleConfig(trim_whitespace=True),
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "\tAnswer\n"})])
        assert result.results[0].total_points == 10.0


class TestExactMatchSchemaValidation:
    """Test ExactMatchRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that ExactMatchRule validates correctly against TEXT schema."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="Paris",
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": TextQuestionSchema(),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert len(errors) == 0

    def test_validate_incompatible_choice_schema(self):
        """Test that ExactMatchRule rejects CHOICE schema."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="A",
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(options=["A", "B", "C"]),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "TEXT" in errors[0]
        assert "CHOICE" in errors[0]

    def test_validate_incompatible_numeric_schema(self):
        """Test that ExactMatchRule rejects NUMERIC schema."""
        rule = ExactMatchRule(
            question_id="q1",
            answer="42",
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": NumericQuestionSchema(),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "TEXT" in errors[0]
        assert "NUMERIC" in errors[0]
