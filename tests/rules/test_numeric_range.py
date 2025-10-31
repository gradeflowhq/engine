"""
Tests for NumericRangeRule grading logic.
"""

from gradeflow_engine import NumericRangeRule, Rubric, Submission, grade


class TestNumericRangeRule:
    """Test NumericRangeRule grading logic."""

    def test_exact_value(self):
        """Test exact numeric value."""
        rule = NumericRangeRule(
            question_id="q1",
            correct_value=3.14,
            tolerance=0.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "3.14"})])
        assert result.results[0].total_points == 10.0

    def test_tolerance(self):
        """Test numeric tolerance."""
        rule = NumericRangeRule(
            question_id="q1",
            correct_value=100.0,
            tolerance=5.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Within tolerance
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "103"})])
        assert result.results[0].total_points == 10.0

        # Outside tolerance
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "106"})])
        assert result.results[0].total_points == 0.0

    def test_partial_credit(self):
        """Test partial credit ranges."""
        rule = NumericRangeRule(
            question_id="q1",
            correct_value=100.0,
            tolerance=0.0,
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
            correct_value=10.0,
            tolerance=1.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "not a number"})])
        assert result.results[0].total_points == 0.0

    def test_scientific_notation(self):
        """Test scientific notation input."""
        rule = NumericRangeRule(
            question_id="q1",
            correct_value=1000.0,
            tolerance=10.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "1e3"})])
        assert result.results[0].total_points == 10.0

    def test_negative_numbers(self):
        """Test negative numbers."""
        rule = NumericRangeRule(
            question_id="q1",
            correct_value=-5.0,
            tolerance=1.0,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "-4.5"})])
        assert result.results[0].total_points == 10.0

    def test_very_large_numbers(self):
        """Test very large numbers."""
        rule = NumericRangeRule(
            question_id="q1",
            correct_value=1e100,
            tolerance=1e98,
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
            correct_value=0.0,
            tolerance=0.0,
            max_points=10.0,
            description="Negative zero test",
            unit="units",
        )
        rubric = Rubric(name="Test", rules=[rule])
        # -0.0 == 0.0 in Python
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "-0.0"})])
        assert result.results[0].total_points == 10.0
        assert result.results[0].total_points == 10.0
