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
            min_length=5,
            max_length=5,
            mode="words",
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
            min_length=3,
            max_length=7,
            mode="words",
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
            min_length=10,
            max_length=20,
            mode="characters",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This is 15 char"})]
        )  # within 10..20 characters
        assert result.results[0].total_points == 10.0

    def test_sentence_count(self):
        """Test with a word-based limit for multi-sentence answer."""
        rule = LengthRule(
            question_id="q1",
            min_length=2,
            max_length=10,
            mode="words",
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
            min_length=5,
            max_length=10,
            mode="words",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": ""})])
        assert result.results[0].total_points == 0.0

    def test_whitespace_only(self):
        """Test with whitespace-only answer."""
        rule = LengthRule(
            question_id="q1",
            min_length=1,
            max_length=10,
            mode="words",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "   \n\t  "})])
        assert result.results[0].total_points == 0.0

    def test_only_char_limit(self):
        """Test with only character limit specified."""
        rule = LengthRule(
            question_id="q1",
            min_length=5,
            max_length=15,
            mode="characters",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Hello!"})])
        assert result.results[0].total_points == 10.0

    def test_too_long(self):
        """Test answer that's too long (word-based)."""
        rule = LengthRule(
            question_id="q1",
            min_length=1,
            max_length=3,
            mode="words",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This is way too long"})]
        )
        assert result.results[0].total_points == 0.0

    def test_character_limits_min(self):
        """Test minimum character limit and feedback wording."""
        rule = LengthRule(question_id="q1", min_length=20, mode="characters", max_points=10.0)

        rubric = Rubric(name="Test", rules=[rule])

        # Too few characters
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Short"})])
        assert result.results[0].total_points == 0.0
        fb = result.results[0].grade_details[0].feedback or ""
        assert "Too short" in fb
        assert "characters" in fb  # expected string includes mode

        # Enough characters
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This has enough characters"})]
        )
        assert result.results[0].total_points == 10.0

    def test_character_limits_max(self):
        """Test maximum character limit and feedback wording."""
        rule = LengthRule(question_id="q1", max_length=10, mode="characters", max_points=10.0)

        rubric = Rubric(name="Test", rules=[rule])

        # Too many characters
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This is way too long"})]
        )
        assert result.results[0].total_points == 0.0
        fb = result.results[0].grade_details[0].feedback or ""
        assert "Too long" in fb
        assert "characters" in fb

        # Within limit
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Short"})])
        assert result.results[0].total_points == 10.0

    def test_multiple_violations_yield_zero(self):
        """Multiple violations result in zero points (no per-violation deduction)."""
        # Use a word-based rule with a range that will be violated
        rule = LengthRule(
            question_id="q1",
            min_length=5,
            max_length=10,
            mode="words",
            max_points=10.0,
        )

        rubric = Rubric(name="Test", rules=[rule])

        # Answer with too few words (and thus violates)
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Hi"})])
        assert result.results[0].total_points == 0.0


class TestLengthSchemaValidation:
    """Test LengthRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that LengthRule validates correctly against TEXT schema."""
        rule = LengthRule(
            question_id="q1",
            min_length=10,
            max_length=50,
            mode="words",
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": TextQuestionSchema(),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert errors == []

    def test_validate_incompatible_choice_schema(self):
        """Test that LengthRule rejects CHOICE schema."""
        rule = LengthRule(
            question_id="q1",
            min_length=1,
            max_length=10,
            mode="characters",
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
        assert "CHOICE" in errors[0]

    def test_validate_incompatible_numeric_schema(self):
        """Test that LengthRule rejects NUMERIC schema."""
        rule = LengthRule(
            question_id="q1",
            min_length=5,
            max_length=10,
            mode="words",
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
        assert "NUMERIC" in errors[0]
