"""
Tests for KeywordRule grading logic.
"""

from gradeflow_engine import KeywordRule, Rubric, Submission, grade


class TestKeywordRule:
    """Test KeywordRule grading logic."""

    def test_required_keywords(self):
        """Test required keywords."""
        rule = KeywordRule(
            question_id="q1",
            required_keywords=["python", "programming"],
            points_per_required=5.0,
            case_sensitive=False,
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Both keywords present
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "Python programming is fun"})]
        )
        assert result.results[0].total_points == 10.0
        assert result.results[0].grade_details[0].is_correct

        # One keyword missing
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "Python is fun"})])
        assert result.results[0].total_points == 5.0
        assert not result.results[0].grade_details[0].is_correct

    def test_optional_keywords(self):
        """Test optional bonus keywords."""
        rule = KeywordRule(
            question_id="q1",
            required_keywords=[],
            optional_keywords=["advanced", "expert", "professional"],
            points_per_optional=2.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric,
            [Submission(student_id="s1", answers={"q1": "An advanced professional approach"})],
        )
        assert result.results[0].total_points == 4.0  # 2 keywords * 2 points

    def test_max_optional_points(self):
        """Test max optional points cap."""
        rule = KeywordRule(
            question_id="q1",
            required_keywords=[],
            optional_keywords=["a", "b", "c", "d"],
            points_per_optional=3.0,
            max_optional_points=6.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        # All 4 keywords = 12 points, but capped at 6
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "a b c d"})])
        assert result.results[0].total_points == 6.0
