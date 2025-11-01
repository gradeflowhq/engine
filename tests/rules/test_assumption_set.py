"""
Tests for AssumptionSetRule grading logic.
"""

from gradeflow_engine import (
    AnswerSet,
    AssumptionSetRule,
    ExactMatchRule,
    Rubric,
    Submission,
    grade,
)


class TestAssumptionSetRule:
    """Test AssumptionSetRule grading logic."""

    def test_matching_assumption_set(self):
        """Test grading with matching assumption set."""
        rule = AssumptionSetRule(
            question_ids=["q1", "q2"],
            answer_sets=[
                AnswerSet(
                    name="Set 1",
                    answers={
                        "q1": ExactMatchRule(
                            question_id="q1",
                            correct_answer="A",
                            max_points=5.0,
                        ),
                        "q2": ExactMatchRule(
                            question_id="q2",
                            correct_answer="X",
                            max_points=5.0,
                        ),
                    },
                ),
                AnswerSet(
                    name="Set 2",
                    answers={
                        "q1": ExactMatchRule(
                            question_id="q1",
                            correct_answer="B",
                            max_points=5.0,
                        ),
                        "q2": ExactMatchRule(
                            question_id="q2",
                            correct_answer="Y",
                            max_points=5.0,
                        ),
                    },
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # Matches first set
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A", "q2": "X"})])
        assert result.results[0].total_points == 10.0

        # Matches second set
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "B", "q2": "Y"})])
        assert result.results[0].total_points == 10.0

    def test_no_matching_assumption_set(self):
        """Test when no assumption set matches."""
        rule = AssumptionSetRule(
            question_ids=["q1", "q2"],
            answer_sets=[
                AnswerSet(
                    name="Set 1",
                    answers={
                        "q1": ExactMatchRule(
                            question_id="q1",
                            correct_answer="A",
                            max_points=5.0,
                        ),
                        "q2": ExactMatchRule(
                            question_id="q2",
                            correct_answer="X",
                            max_points=5.0,
                        ),
                    },
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # No match
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "C", "q2": "Z"})])
        assert result.results[0].total_points == 0.0
