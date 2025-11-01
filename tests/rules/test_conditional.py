"""
Tests for ConditionalRule grading logic.
"""

from gradeflow_engine import ConditionalRule, ExactMatchRule, Rubric, Submission, grade


class TestConditionalRule:
    """Test ConditionalRule grading logic."""

    def test_condition_met(self):
        """Test conditional grading when condition is met."""
        rule = ConditionalRule(
            if_rules={
                "q1": ExactMatchRule(
                    question_id="q1",
                    correct_answer="A",
                    max_points=1.0,
                )
            },
            then_rules={
                "q2": ExactMatchRule(
                    question_id="q2",
                    correct_answer="B",
                    max_points=10.0,
                )
            },
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Condition met, correct answer
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A", "q2": "B"})])
        assert result.results[0].total_points == 10.0

        # Condition met, wrong answer
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "A", "q2": "C"})])
        assert result.results[0].total_points == 0.0

    def test_condition_not_met(self):
        """Test conditional grading when condition is not met."""
        rule = ConditionalRule(
            if_rules={
                "q1": ExactMatchRule(
                    question_id="q1",
                    correct_answer="A",
                    max_points=1.0,
                )
            },
            then_rules={
                "q2": ExactMatchRule(
                    question_id="q2",
                    correct_answer="B",
                    max_points=10.0,
                )
            },
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Condition not met - rule doesn't apply
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "C", "q2": "X"})])
        assert result.results[0].total_points == 0.0
