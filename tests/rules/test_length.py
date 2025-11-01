"""
Tests for LengthRule grading logic.
"""

from gradeflow_engine import LengthRule, Rubric, Submission, grade
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestLengthRule:
    """Test LengthRule grading logic."""

    def test_word_count_exact(self):
        """Test exact word count."""
        rule = LengthRule(
            question_id="q1",
            min_words=5,
            max_words=5,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This is exactly five words"})]
        )
        assert result.results[0].total_points == 10.0

        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "Too short"})])
        assert result.results[0].total_points == 0.0

    def test_word_count_range(self):
        """Test word count range."""
        rule = LengthRule(
            question_id="q1",
            min_words=3,
            max_words=7,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This has five words exactly"})]
        )
        assert result.results[0].total_points == 10.0

    def test_character_count(self):
        """Test character count."""
        rule = LengthRule(
            question_id="q1",
            min_chars=10,
            max_chars=20,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This is 15 char"})]
        )  # 15 chars
        assert result.results[0].total_points == 10.0

    def test_sentence_count(self):
        """Test with both word and char limits."""
        rule = LengthRule(
            question_id="q1",
            min_words=2,
            max_words=10,
            min_chars=10,
            max_chars=50,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric,
            [Submission(student_id="s1", answers={"q1": "First sentence. Second sentence."})],
        )
        assert result.results[0].total_points == 10.0

    def test_empty_answer(self):
        """Test with empty answer."""
        rule = LengthRule(
            question_id="q1",
            min_words=5,
            max_words=10,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": ""})])
        assert result.results[0].total_points == 0.0

    def test_whitespace_only(self):
        """Test with whitespace-only answer."""
        rule = LengthRule(
            question_id="q1",
            min_words=1,
            max_words=10,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "   \n\t  "})])
        assert result.results[0].total_points == 0.0

    def test_only_char_limit(self):
        """Test with only character limit specified."""
        rule = LengthRule(
            question_id="q1",
            min_chars=5,
            max_chars=15,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Hello!"})])
        assert result.results[0].total_points == 10.0

    def test_too_long(self):
        """Test answer that's too long."""
        rule = LengthRule(
            question_id="q1",
            min_words=1,
            max_words=3,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This is way too long"})]
        )
        assert result.results[0].total_points == 0.0

    def test_character_limits_min(self):
        """Test minimum character limit."""
        rule = LengthRule(question_id="q1", min_chars=20, max_points=10.0, description="Test")

        rubric = Rubric(name="Test", rules=[rule])

        # Too few characters
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Short"})])
        assert result.results[0].total_points == 0.0
        assert "Too few characters" in result.results[0].grade_details[0].feedback

        # Enough characters
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This has enough characters"})]
        )
        assert result.results[0].total_points == 10.0

    def test_character_limits_max(self):
        """Test maximum character limit."""
        rule = LengthRule(question_id="q1", max_chars=10, max_points=10.0, description="Test")

        rubric = Rubric(name="Test", rules=[rule])

        # Too many characters
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This is way too long"})]
        )
        assert result.results[0].total_points == 0.0
        assert "Too many characters" in result.results[0].grade_details[0].feedback

        # Within limit
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Short"})])
        assert result.results[0].total_points == 10.0

    def test_deduct_per_violation(self):
        """Test deducting points per violation."""
        rule = LengthRule(
            question_id="q1",
            min_words=5,
            max_words=10,
            min_chars=20,
            max_chars=50,
            max_points=10.0,
            strict=False,
            deduct_per_violation=2.0,
            description="Test",
        )

        rubric = Rubric(name="Test", rules=[rule])

        # Answer with 2 violations: too few words and too few chars
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Hi"})])
        # Should deduct 2.0 * 2 = 4.0 points
        assert result.results[0].total_points == 6.0

    def test_deduct_per_violation_max_cap(self):
        """Test that deductions don't exceed max_points."""
        rule = LengthRule(
            question_id="q1",
            min_words=5,
            max_words=10,
            min_chars=20,
            max_chars=50,
            max_points=5.0,
            strict=False,
            deduct_per_violation=10.0,  # Very high deduction
            description="Test",
        )

        rubric = Rubric(name="Test", rules=[rule])

        # Answer with violations
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Hi"})])
        # Deduction would be 20.0 but capped at max_points (5.0)
        assert result.results[0].total_points == 0.0


class TestLengthSchemaValidation:
    """Test LengthRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that LengthRule validates correctly against TEXT schema."""
        rule = LengthRule(
            question_id="q1",
            min_words=10,
            max_words=50,
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": TextQuestionSchema(question_id="q1", max_length=500),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert errors == []

    def test_validate_incompatible_choice_schema(self):
        """Test that LengthRule rejects CHOICE schema."""
        rule = LengthRule(
            question_id="q1",
            min_chars=1,
            max_chars=10,
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A", "B", "C"]),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "CHOICE" in errors[0]

    def test_validate_incompatible_numeric_schema(self):
        """Test that LengthRule rejects NUMERIC schema."""
        rule = LengthRule(
            question_id="q1",
            min_words=5,
            max_words=10,
            max_points=10.0,
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
