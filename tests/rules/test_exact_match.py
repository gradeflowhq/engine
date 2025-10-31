"""
Tests for ExactMatchRule grading logic.
"""

from gradeflow_engine import ExactMatchRule, Rubric, Submission, grade


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
