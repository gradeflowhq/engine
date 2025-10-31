"""
Tests for MultipleChoiceRule grading logic.
"""

from gradeflow_engine import MultipleChoiceRule, Rubric, Submission, grade


class TestMultipleChoiceRule:
    """Test MultipleChoiceRule grading logic."""

    def test_all_or_nothing_single_correct(self):
        """Test all-or-nothing with single correct answer."""
        rule = MultipleChoiceRule(
            question_id="q1",
            correct_answers=["B"],
            max_points=10.0,
            scoring_mode="all_or_nothing",
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "B"})])
        assert result.results[0].total_points == 10.0

        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "A"})])
        assert result.results[0].total_points == 0.0

    def test_all_or_nothing_multiple_correct(self):
        """Test all-or-nothing with multiple correct answers."""
        rule = MultipleChoiceRule(
            question_id="q1",
            correct_answers=["A", "C"],
            max_points=10.0,
            scoring_mode="all_or_nothing",
        )
        rubric = Rubric(name="Test", rules=[rule])
        # All correct
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A,C"})])
        assert result.results[0].total_points == 10.0

        # Partial
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "A"})])
        assert result.results[0].total_points == 0.0

    def test_partial_scoring(self):
        """Test partial credit scoring."""
        rule = MultipleChoiceRule(
            question_id="q1",
            correct_answers=["A", "B", "C"],
            max_points=12.0,
            scoring_mode="partial",
        )
        rubric = Rubric(name="Test", rules=[rule])
        # All correct
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A,B,C"})])
        assert result.results[0].total_points == 12.0

        # 2 out of 3
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "A,B"})])
        assert result.results[0].total_points == 8.0

        # 1 out of 3
        result = grade(rubric, [Submission(student_id="s3", answers={"q1": "C"})])
        assert result.results[0].total_points == 4.0

    def test_negative_scoring(self):
        """Test negative scoring for wrong answers."""
        rule = MultipleChoiceRule(
            question_id="q1",
            correct_answers=["A", "B"],
            max_points=10.0,
            scoring_mode="negative",
            penalty_per_wrong=2.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        # All correct
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A,B"})])
        assert result.results[0].total_points == 10.0

        # One correct, one wrong
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "A,C"})])
        assert result.results[0].total_points == 3.0  # 5 (partial) - 2 (penalty)

    def test_custom_delimiter(self):
        """Test custom delimiter for answers."""
        rule = MultipleChoiceRule(
            question_id="q1",
            correct_answers=["A", "C"],
            max_points=10.0,
            scoring_mode="all_or_nothing",
            delimiter=";",
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A;C"})])
        assert result.results[0].total_points == 10.0

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        rule = MultipleChoiceRule(
            question_id="q1",
            correct_answers=["A", "B"],
            max_points=10.0,
            scoring_mode="all_or_nothing",
            trim_whitespace=True,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": " A , B "})])
        assert result.results[0].total_points == 10.0

    def test_case_sensitivity(self):
        """Test case-sensitive matching."""
        rule = MultipleChoiceRule(
            question_id="q1",
            correct_answers=["a"],
            max_points=10.0,
            scoring_mode="all_or_nothing",
            case_sensitive=True,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A"})])
        assert result.results[0].total_points == 0.0

        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "a"})])
        assert result.results[0].total_points == 10.0
