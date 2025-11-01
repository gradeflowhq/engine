"""
Tests for ExactMatchRule grading logic.
"""

from gradeflow_engine import ExactMatchRule, Rubric, Submission, grade
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
            correct_answer="Paris",
            max_points=10.0,
            case_sensitive=False,
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
            correct_answer="Paris",
            max_points=10.0,
            case_sensitive=True,
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
            correct_answer="Paris",
            max_points=10.0,
            trim_whitespace=True,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "  Paris  "})])
        assert result.results[0].total_points == 10.0

    def test_unicode_in_answers(self):
        """Test Unicode characters in answers."""
        rule = ExactMatchRule(
            question_id="q1", correct_answer="café", max_points=10.0, description="Unicode test"
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "café"})])
        assert result.results[0].total_points == 10.0

    def test_emoji_in_answers(self):
        """Test emoji in answers."""
        rule = ExactMatchRule(
            question_id="q1",
            correct_answer="Hello 👋",
            max_points=5.0,
            case_sensitive=False,
            description="Emoji test",
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "hello 👋"})])
        assert result.results[0].total_points == 5.0

    def test_internal_whitespace_preserved(self):
        """Test that internal whitespace is preserved."""
        rule = ExactMatchRule(
            question_id="q1",
            correct_answer="New York",
            max_points=10.0,
            description="Internal whitespace",
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "New York"})])
        assert result.results[0].total_points == 10.0

    def test_tabs_and_newlines(self):
        """Test handling of tabs and newlines in trimming."""
        rule = ExactMatchRule(
            question_id="q1",
            correct_answer="Answer",
            max_points=10.0,
            trim_whitespace=True,
            description="Tab/newline test",
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
            correct_answer="Paris",
            max_points=10.0,
            description="Text question",
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": TextQuestionSchema(question_id="q1", max_length=100),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert errors == []

    def test_validate_against_choice_schema(self):
        """Test that ExactMatchRule validates correctly against CHOICE schema."""
        rule = ExactMatchRule(
            question_id="q1",
            correct_answer="A",
            max_points=10.0,
            description="Choice question",
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A", "B", "C"]),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert errors == []

    def test_validate_incompatible_numeric_schema(self):
        """Test that ExactMatchRule rejects NUMERIC schema."""
        rule = ExactMatchRule(
            question_id="q1",
            correct_answer="42",
            max_points=10.0,
            description="Numeric question",
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": NumericQuestionSchema(question_id="q1"),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "NUMERIC" in errors[0]

    def test_validate_choice_answer_in_options(self):
        """Test that ExactMatchRule validates answer is in CHOICE options."""
        rule = ExactMatchRule(
            question_id="q1",
            correct_answer="D",  # Not in options
            max_points=10.0,
            description="Invalid choice",
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A", "B", "C"]),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert len(errors) == 1
        assert "not in schema options" in errors[0]
        assert "D" in errors[0]
