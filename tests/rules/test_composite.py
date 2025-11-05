"""
Tests for CompositeRule grading logic.
"""

from gradeflow_engine import (
    CompositeRule,
    ExactMatchRule,
    KeywordRule,
    LengthRule,
    Rubric,
    Submission,
    grade,
)
from gradeflow_engine.schema import (
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestCompositeRule:
    """Test CompositeRule grading logic."""

    def test_and_mode(self):
        """Test AND composition - all rules must pass."""
        rule = CompositeRule(
            question_id="q1",
            mode="AND",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="Paris", max_points=5.0),
                LengthRule(
                    question_id="q1",
                    length_type="character",
                    min_length=3,
                    max_length=10,
                    max_points=5.0,
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Both rules pass
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 10.0

        # First rule fails
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "London"})])
        assert result.results[0].total_points == 0.0

    def test_or_mode(self):
        """Test OR composition - any rule passing awards points."""
        rule = CompositeRule(
            question_id="q1",
            mode="OR",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="Paris", max_points=10.0),
                ExactMatchRule(question_id="q1", correct_answer="France", max_points=10.0),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])
        # First rule passes
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 10.0

        # Second rule passes
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "France"})])
        assert result.results[0].total_points == 10.0

        # No rules pass
        result = grade(rubric, [Submission(student_id="s3", answers={"q1": "London"})])
        assert result.results[0].total_points == 0.0

    def test_weighted_mode(self):
        """Test WEIGHTED composition - weighted average of all rules."""
        rule = CompositeRule(
            question_id="q1",
            mode="WEIGHTED",
            rules=[
                KeywordRule(
                    question_id="q1",
                    required_keywords=["python"],
                    points_per_required=5.0,
                ),
                LengthRule(
                    question_id="q1",
                    min_words=3,
                    max_words=10,
                    max_points=3.0,
                ),
            ],
            weights=[0.5, 0.5],
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Both rules award points: keyword=5.0, length=3.0
        # Weighted with [0.5, 0.5]:
        # points = 5.0*0.5 + 3.0*0.5 = 4.0
        # max = 5.0*0.5 + 3.0*0.5 = 4.0
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "I love Python programming"})]
        )
        assert result.results[0].total_points == 4.0

    def test_nested_composite(self):
        """Test nested composite rules."""
        rule = CompositeRule(
            question_id="q1",
            mode="AND",
            rules=[
                ExactMatchRule(
                    question_id="q1", correct_answer="Paris", max_points=5.0, case_sensitive=False
                ),
                CompositeRule(
                    question_id="q1",
                    mode="OR",
                    rules=[
                        LengthRule(
                            question_id="q1",
                            length_type="character",
                            min_length=5,
                            max_length=5,
                            max_points=5.0,
                        ),
                        KeywordRule(
                            question_id="q1",
                            required_keywords=["city"],
                            required_points_per_keyword=5.0,
                        ),
                    ],
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Outer AND: needs "Paris" AND (length=5 OR keyword="city")
        # This should pass: "Paris" matches and length is 5
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 10.0

    def test_composite_with_min_passing(self):
        """Test composite rule with min_passing requirement in OR mode."""
        rule = CompositeRule(
            question_id="q1",
            mode="OR",
            min_passing=2,
            description="At least 2 rules must pass",
            rules=[
                ExactMatchRule(
                    question_id="q1", correct_answer="A", max_points=10.0, description="Option A"
                ),
                ExactMatchRule(
                    question_id="q1", correct_answer="B", max_points=10.0, description="Option B"
                ),
                ExactMatchRule(
                    question_id="q1", correct_answer="C", max_points=10.0, description="Option C"
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # Only 1 rule can pass with single answer "A", but min_passing requires 2
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A"})])
        assert result.results[0].total_points == 0.0


class TestCompositeSchemaValidation:
    """Test CompositeRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that CompositeRule validates correctly against TEXT schema."""
        rule = CompositeRule(
            question_id="q1",
            mode="AND",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="Paris", max_points=5.0),
                LengthRule(question_id="q1", min_words=1, max_words=10, max_points=5.0),
            ],
        )
        schema = TextQuestionSchema()

        errors = rule.validate_against_schema("q1", schema, "Rule 1")
        assert errors == []

    def test_validate_incompatible_choice_schema(self):
        """Test that CompositeRule rejects CHOICE schema when sub-rules are incompatible."""
        rule = CompositeRule(
            question_id="q1",
            mode="OR",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="A", max_points=10.0),
                ExactMatchRule(question_id="q1", correct_answer="B", max_points=10.0),
            ],
        )
        schema = ChoiceQuestionSchema(options=["A", "B", "C"])

        errors = rule.validate_against_schema("q1", schema, "Rule 1")
        assert len(errors) == 2
        for error in errors:
            assert "only compatible with" in error
            assert "TEXT" in error
            assert "CHOICE" in error

    def test_validate_incompatible_numeric_schema(self):
        """Test that CompositeRule rejects NUMERIC schema when sub-rules are incompatible."""
        rule = CompositeRule(
            question_id="q1",
            mode="AND",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="text", max_points=5.0),
            ],
        )
        schema = NumericQuestionSchema()

        errors = rule.validate_against_schema("q1", schema, "Rule 1")
        assert len(errors) > 0
        assert any("only compatible with" in error for error in errors)
