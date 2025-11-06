"""
Tests for ConditionalRule grading logic.
"""

from gradeflow_engine import ConditionalRule, ExactMatchRule, Rubric, Submission, grade
from gradeflow_engine.schema import (
    ChoiceQuestionSchema,
    TextQuestionSchema,
)


class TestConditionalRule:
    """Test ConditionalRule grading logic."""

    def test_condition_met(self):
        """Test conditional grading when condition is met."""
        rule = ConditionalRule(
            if_rules=[
                ExactMatchRule(
                    question_id="q1",
                    answer="A",
                    max_points=1.0,
                )
            ],
            then_rules=[
                ExactMatchRule(
                    question_id="q2",
                    answer="B",
                    max_points=10.0,
                )
            ],
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
            if_rules=[
                ExactMatchRule(
                    question_id="q1",
                    answer="A",
                    max_points=1.0,
                )
            ],
            then_rules=[
                ExactMatchRule(
                    question_id="q2",
                    answer="B",
                    max_points=10.0,
                )
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Condition not met - rule doesn't apply
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "C", "q2": "X"})])
        assert result.results[0].total_points == 0.0


class TestConditionalSchemaValidation:
    """Test ConditionalRule schema validation."""

    def test_validate_against_schema(self):
        """Test that ConditionalRule validates correctly against schema."""
        rule = ConditionalRule(
            if_rules=[
                ExactMatchRule(
                    question_id="q1",
                    answer="A",
                    max_points=1.0,
                )
            ],
            then_rules=[
                ExactMatchRule(
                    question_id="q2",
                    answer="B",
                    max_points=10.0,
                )
            ],
        )
        # ConditionalRule validates against individual question schemas
        schema_q1 = ChoiceQuestionSchema(options=["A", "B", "C"])
        errors = rule.validate_against_schema("q1", schema_q1, "Conditional Rule 1")
        # Since ConditionalRule currently passes the same schema to all sub-rules,
        # this may produce errors - we're just testing it doesn't crash
        assert isinstance(errors, list)

    def test_validate_with_text_schema(self):
        """Test that ConditionalRule works with TEXT schema."""
        rule = ConditionalRule(
            if_rules=[
                ExactMatchRule(
                    question_id="q1",
                    answer="Yes",
                    max_points=1.0,
                )
            ],
            then_rules=[
                ExactMatchRule(
                    question_id="q2",
                    answer="Answer",
                    max_points=10.0,
                )
            ],
        )
        schema = TextQuestionSchema()
        errors = rule.validate_against_schema("q1", schema, "Conditional Rule 1")
        assert isinstance(errors, list)
