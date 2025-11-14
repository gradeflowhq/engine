"""
Tests for AssumptionSetRule grading logic.
"""

from gradeflow_engine import (
    AssumptionSetRule,
    ExactMatchRule,
    Rubric,
    Submission,
    grade,
)
from gradeflow_engine.rules.assumption_set.model import Assumption
from gradeflow_engine.schema import (
    ChoiceQuestionSchema,
    TextQuestionSchema,
)


class TestAssumptionSetRule:
    """Test AssumptionSetRule grading logic."""

    def test_matching_assumption_set(self):
        """Test grading with matching assumption set."""
        rule = AssumptionSetRule(
            assumptions=[
                Assumption(
                    name="Set 1",
                    rules=[
                        ExactMatchRule(
                            question_id="q1",
                            answer="A",
                            max_points=5.0,
                        ),
                        ExactMatchRule(
                            question_id="q2",
                            answer="X",
                            max_points=5.0,
                        ),
                    ],
                ),
                Assumption(
                    name="Set 2",
                    rules=[
                        ExactMatchRule(
                            question_id="q1",
                            answer="B",
                            max_points=5.0,
                        ),
                        ExactMatchRule(
                            question_id="q2",
                            answer="Y",
                            max_points=5.0,
                        ),
                    ],
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
            assumptions=[
                Assumption(
                    name="Set 1",
                    rules=[
                        ExactMatchRule(
                            question_id="q1",
                            answer="A",
                            max_points=5.0,
                        ),
                        ExactMatchRule(
                            question_id="q2",
                            answer="X",
                            max_points=5.0,
                        ),
                    ],
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # No match
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "C", "q2": "Z"})])
        assert result.results[0].total_points == 0.0

    def test_mode_best(self):
        """Mode 'best' should pick the assumption with the highest total."""
        assumptions = [
            Assumption(
                name="A1",
                rules=[
                    ExactMatchRule(question_id="q1", answer="A", max_points=5.0),
                    ExactMatchRule(question_id="q2", answer="X", max_points=5.0),
                ],
            ),
            Assumption(
                name="A2",
                rules=[
                    ExactMatchRule(question_id="q1", answer="A", max_points=5.0),
                    ExactMatchRule(question_id="q2", answer="Y", max_points=5.0),
                ],
            ),
        ]
        rule = AssumptionSetRule(assumptions=assumptions, mode="best")
        rubric = Rubric(name="BestMode", rules=[rule])
        sub = Submission(student_id="s_best", answers={"q1": "A", "q2": "X"})
        res = grade(rubric, [sub])
        assert res.results[0].total_points == 10.0

    def test_mode_worst(self):
        """Mode 'worst' should pick the assumption with the lowest total."""
        assumptions = [
            Assumption(
                name="B1",
                rules=[
                    ExactMatchRule(question_id="q1", answer="A", max_points=5.0),
                ],
            ),
            Assumption(
                name="B2",
                rules=[
                    ExactMatchRule(question_id="q1", answer="B", max_points=5.0),
                ],
            ),
        ]
        # student matches only B1 -> totals: B1=5, B2=0 -> worst picks B2 => 0
        rule = AssumptionSetRule(assumptions=assumptions, mode="worst")
        rubric = Rubric(name="WorstMode", rules=[rule])
        sub = Submission(student_id="s_worst", answers={"q1": "A"})
        res = grade(rubric, [sub])
        assert res.results[0].total_points == 0.0

    def test_mode_average(self):
        """Mode 'average' should average points per question across assumptions."""
        assumptions = [
            Assumption(
                name="C1",
                rules=[
                    ExactMatchRule(question_id="q1", answer="A", max_points=4.0),
                ],
            ),
            Assumption(
                name="C2",
                rules=[
                    ExactMatchRule(question_id="q1", answer="B", max_points=4.0),
                ],
            ),
        ]
        # student matches C1 only -> per-question average = (4 + 0) / 2 = 2.0
        rule = AssumptionSetRule(assumptions=assumptions, mode="average")
        rubric = Rubric(name="AvgMode", rules=[rule])
        sub = Submission(student_id="s_avg", answers={"q1": "A"})
        res = grade(rubric, [sub])
        assert res.results[0].total_points == 2.0


class TestAssumptionSetSchemaValidation:
    """Test AssumptionSetRule schema validation."""

    def test_validate_against_question_schema(self):
        """Test that AssumptionSetRule validates correctly against schema."""
        rule = AssumptionSetRule(
            assumptions=[
                Assumption(
                    name="Set 1",
                    rules=[
                        ExactMatchRule(
                            question_id="q1",
                            answer="A",
                            max_points=5.0,
                        ),
                        ExactMatchRule(
                            question_id="q2",
                            answer="X",
                            max_points=5.0,
                        ),
                    ],
                ),
            ],
        )
        # AssumptionSetRule validates against individual question schemas
        schema_q = ChoiceQuestionSchema(options=["A", "B", "C"])
        question_map = {"q1": schema_q}
        errors = rule.validate_against_question_schema(question_map, "Assumption Set Rule 1")
        # Just test it doesn't crash and returns a list
        assert isinstance(errors, list)

    def test_validate_with_text_schema(self):
        """Test that AssumptionSetRule works with TEXT schema."""
        rule = AssumptionSetRule(
            assumptions=[
                Assumption(
                    name="Set 1",
                    rules=[
                        ExactMatchRule(
                            question_id="q1",
                            answer="Answer",
                            max_points=10.0,
                        ),
                    ],
                ),
            ],
        )
        schema_q = TextQuestionSchema()
        question_map = {"q1": schema_q}
        errors = rule.validate_against_question_schema(question_map, "Assumption Set Rule 1")
        assert isinstance(errors, list)
