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
from gradeflow_engine.schema import (
    ChoiceQuestionSchema,
    TextQuestionSchema,
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


class TestAssumptionSetSchemaValidation:
    """Test AssumptionSetRule schema validation."""

    def test_validate_against_schema(self):
        """Test that AssumptionSetRule validates correctly against schema."""
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
        # AssumptionSetRule validates against individual question schemas
        schema = ChoiceQuestionSchema(options=["A", "B", "C"])
        errors = rule.validate_against_schema("q1", schema, "Assumption Set Rule 1")
        # Just test it doesn't crash and returns a list
        assert isinstance(errors, list)

    def test_validate_with_text_schema(self):
        """Test that AssumptionSetRule works with TEXT schema."""
        rule = AssumptionSetRule(
            question_ids=["q1"],
            answer_sets=[
                AnswerSet(
                    name="Set 1",
                    answers={
                        "q1": ExactMatchRule(
                            question_id="q1",
                            correct_answer="Answer",
                            max_points=10.0,
                        ),
                    },
                ),
            ],
        )
        schema = TextQuestionSchema()
        errors = rule.validate_against_schema("q1", schema, "Assumption Set Rule 1")
        assert isinstance(errors, list)
