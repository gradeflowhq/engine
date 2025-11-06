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

    def test_sum_mode(self):
        """Test SUM mode - sum of sub-rule points."""
        rule = CompositeRule(
            question_id="q1",
            mode="sum",
            rules=[
                ExactMatchRule(question_id="q1", answer="Paris", max_points=5.0),
                LengthRule(
                    question_id="q1", min_length=1, max_length=10, mode="words", max_points=5.0
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # Both rules pass -> 5 + 5 = 10
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 10.0

        # Only length rule passes -> 0 + 5 = 5
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "London"})])
        assert result.results[0].total_points == 5.0

    def test_max_mode(self):
        """Test MAX mode - best single sub-rule determines points."""
        rule = CompositeRule(
            question_id="q1",
            mode="max",
            rules=[
                ExactMatchRule(question_id="q1", answer="Paris", max_points=10.0),
                ExactMatchRule(question_id="q1", answer="France", max_points=8.0),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # Best match awards 10
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 10.0

        # No match -> 0
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "London"})])
        assert result.results[0].total_points == 0.0

    def test_average_mode(self):
        """Test AVERAGE mode - average of sub-rule points."""
        rule = CompositeRule(
            question_id="q1",
            mode="average",
            rules=[
                KeywordRule(question_id="q1", keywords=["python"], max_points=5.0),
                LengthRule(
                    question_id="q1", min_length=3, max_length=10, mode="characters", max_points=3.0
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # Both sub-rules match -> (5 + 3) / 2 = 4.0
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "python 3"})])
        assert result.results[0].total_points == 4.0

    def test_multiply_mode(self):
        """Test MULTIPLY mode - product of normalized scores scaled by avg max."""
        rule = CompositeRule(
            question_id="q1",
            mode="multiply",
            rules=[
                KeywordRule(question_id="q1", keywords=["city"], max_points=5.0),
                LengthRule(
                    question_id="q1", min_length=1, max_length=10, mode="characters", max_points=5.0
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # If both fully match, product_fraction == 1 -> points = avg_max = (5+3)/2 = 4.0
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "city car"})])
        assert result.results[0].total_points == 25.0

    def test_min_mode(self):
        """Test MIN mode - weakest sub-rule determines points."""
        rule = CompositeRule(
            question_id="q1",
            mode="min",
            rules=[
                ExactMatchRule(question_id="q1", answer="Paris", max_points=5.0),
                LengthRule(
                    question_id="q1", min_length=1, max_length=10, mode="words", max_points=5.0
                ),
            ],
        )
        rubric = Rubric(name="Test", rules=[rule])

        # Both pass -> min(5,5) = 5
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 5.0

        # Exact match fails but length passes -> min(0,5) = 0
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "London"})])
        assert result.results[0].total_points == 0.0

    def test_nested_composite(self):
        """Test nested composite rules."""
        inner = CompositeRule(
            question_id="q1",
            mode="max",
            rules=[
                LengthRule(
                    question_id="q1", min_length=5, max_length=10, mode="characters", max_points=5.0
                ),
                ExactMatchRule(question_id="q1", answer="city", max_points=5.0),
            ],
        )
        outer = CompositeRule(
            question_id="q1",
            mode="sum",
            rules=[
                ExactMatchRule(question_id="q1", answer="Paris", max_points=5.0),
                inner,
            ],
        )
        rubric = Rubric(name="Test", rules=[outer])

        # "Paris" has length 5 and matches exact -> inner max=5, outer sum = 5 + 5 = 10
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 10.0


class TestCompositeSchemaValidation:
    """Test CompositeRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that CompositeRule validates correctly against TEXT schema."""
        rule = CompositeRule(
            question_id="q1",
            mode="sum",
            rules=[
                ExactMatchRule(question_id="q1", answer="Paris", max_points=5.0),
                LengthRule(
                    question_id="q1", min_length=1, max_length=10, mode="words", max_points=5.0
                ),
            ],
        )
        schema = TextQuestionSchema()

        errors = rule.validate_against_schema("q1", schema, "Rule 1")
        assert errors == []

    def test_validate_incompatible_choice_schema(self):
        """Test that CompositeRule rejects CHOICE schema when sub-rules are incompatible."""
        rule = CompositeRule(
            question_id="q1",
            mode="max",
            rules=[
                ExactMatchRule(question_id="q1", answer="A", max_points=10.0),
                ExactMatchRule(question_id="q1", answer="B", max_points=10.0),
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
            mode="sum",
            rules=[
                ExactMatchRule(question_id="q1", answer="text", max_points=5.0),
            ],
        )
        schema = NumericQuestionSchema()

        errors = rule.validate_against_schema("q1", schema, "Rule 1")
        assert len(errors) > 0
        assert any("only compatible with" in error for error in errors)
