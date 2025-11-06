"""
Tests for ProgrammableRule grading logic.
"""

from gradeflow_engine import ProgrammableRule, Rubric, Submission, grade
from gradeflow_engine.schema import (
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestProgrammableRule:
    """Test ProgrammableRule grading logic."""

    def test_simple_script(self):
        """Test simple programmable grading script."""
        rule = ProgrammableRule(
            question_id="q1",
            code="""
points_awarded = 10.0 if 'python' in answer.lower() else 0.0
feedback = 'Contains Python' if points_awarded > 0 else 'Missing Python'
""",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "I love Python"})])
        assert result.results[0].total_points == 10.0

        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "I love Java"})])
        assert result.results[0].total_points == 0.0

    def test_complex_script(self):
        """Test complex grading logic."""
        rule = ProgrammableRule(
            question_id="q1",
            code="""
words = answer.split()
word_count = len(words)

if word_count >= 50:
    points_awarded = 10.0
    feedback = "Excellent length"
elif word_count >= 30:
    points_awarded = 7.0
    feedback = "Good length"
else:
    points_awarded = 3.0
    feedback = "Too short"
""",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Long answer
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": " ".join(["word"] * 60)})]
        )
        assert result.results[0].total_points == 10.0


class TestProgrammableSchemaValidation:
    """Test ProgrammableRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that ProgrammableRule validates correctly against TEXT schema."""
        rule = ProgrammableRule(
            question_id="q1",
            code="points_awarded = 10.0",
            max_points=10.0,
        )
        schema = TextQuestionSchema()

        errors = rule.validate_against_schema("q1", schema, "Rule 1")
        assert errors == []

    def test_validate_against_choice_schema(self):
        """Test that ProgrammableRule validates correctly against CHOICE schema."""
        rule = ProgrammableRule(
            question_id="q1",
            code="points_awarded = 10.0 if answer == 'A' else 0.0",
            max_points=10.0,
        )
        schema = ChoiceQuestionSchema(options=["A", "B", "C"])

        errors = rule.validate_against_schema("q1", schema, "Rule 1")
        assert errors == []

    def test_validate_against_numeric_schema(self):
        """Test that ProgrammableRule validates correctly against NUMERIC schema."""
        rule = ProgrammableRule(
            question_id="q1",
            code="points_awarded = 10.0 if float(answer) > 50 else 0.0",
            max_points=10.0,
        )
        schema = NumericQuestionSchema()

        errors = rule.validate_against_schema("q1", schema, "Rule 1")
        assert errors == []
