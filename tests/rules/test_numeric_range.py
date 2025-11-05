"""
Tests for NumericRangeRule grading logic.
"""

from gradeflow_engine import NumericRangeRule, Rubric, Submission, grade
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
)


class TestNumericRangeRule:
    """Test NumericRangeRule grading logic."""

    def test_exact_value(self):
        """Test exact numeric value."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=3.14,
            max_value=3.14,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "3.14"})])
        assert result.results[0].total_points == 10.0

    def test_range(self):
        """Test numeric range."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=95.0,
            max_value=105.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Within range
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "103"})])
        assert result.results[0].total_points == 10.0

        # Outside range (above)
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "106"})])
        assert result.results[0].total_points == 0.0

        # Outside range (below)
        result = grade(rubric, [Submission(student_id="s3", answers={"q1": "94"})])
        assert result.results[0].total_points == 0.0

    def test_partial_credit(self):
        """Test partial credit ranges."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=100.0,
            max_value=100.0,
            max_points=10.0,
            partial_credit_ranges=[
                {"min": 98.0, "max": 102.0, "points": 8.0},
                {"min": 95.0, "max": 98.0, "points": 5.0},
                {"min": 102.0, "max": 105.0, "points": 5.0},
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Exact
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "100"})])
        assert result.results[0].total_points == 10.0

        # First partial range (98-102, 8 points) - 101 is in range
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "101"})])
        assert result.results[0].total_points == 8.0

        # Second partial range (95-98, 5 points) - 96 is in range
        result = grade(rubric, [Submission(student_id="s3", answers={"q1": "96"})])
        assert result.results[0].total_points == 5.0

    def test_invalid_input(self):
        """Test invalid numeric input."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=9.0,
            max_value=11.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "not a number"})])
        assert result.results[0].total_points == 0.0

    def test_scientific_notation(self):
        """Test scientific notation input."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=990.0,
            max_value=1010.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "1e3"})])
        assert result.results[0].total_points == 10.0

    def test_negative_numbers(self):
        """Test negative numbers."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=-6.0,
            max_value=-4.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "-4.5"})])
        assert result.results[0].total_points == 10.0

    def test_very_large_numbers(self):
        """Test very large numbers."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=1e100 - 1e98,
            max_value=1e100 + 1e98,
            max_points=5.0,
            description="Large number test",
            unit="units",
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "1e100"})])
        assert result.results[0].total_points == 5.0

    def test_negative_zero(self):
        """Test handling of -0.0."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=0.0,
            max_value=0.0,
            max_points=10.0,
            description="Negative zero test",
            unit="units",
        )
        rubric = Rubric(name="Test", rules=[rule])
        # -0.0 == 0.0 in Python
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "-0.0"})])
        assert result.results[0].total_points == 10.0
        assert result.results[0].total_points == 10.0


class TestNumericRangeSchemaValidation:
    """Test NumericRangeRule schema validation."""

    def test_validate_against_numeric_schema(self):
        """Test that NumericRangeRule validates correctly against NUMERIC schema."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=0.0,
            max_value=100.0,
            max_points=10.0,
            unit="points",
            description="Test",
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": NumericQuestionSchema(),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert errors == []

    def test_validate_incompatible_choice_schema(self):
        """Test that NumericRangeRule rejects CHOICE schema."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=0.0,
            max_value=100.0,
            max_points=10.0,
            unit="points",
            description="Test",
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(options=["A", "B", "C"]),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "NUMERIC" in errors[0]