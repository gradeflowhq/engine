"""
Tests for KeywordRule grading logic.
"""

from gradeflow_engine import KeywordRule, Rubric, Submission, grade
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestKeywordRule:
    """Test KeywordRule grading logic."""

    def test_partial_mode_keyword_scoring(self):
        """Partial mode: points split evenly across keywords."""
        rule = KeywordRule(
            question_id="q1",
            keywords=["python", "programming"],
            mode="partial",
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])

        # Both keywords present -> full points
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "Python programming is fun"})]
        )
        assert result.results[0].total_points == 10.0
        assert result.results[0].grade_details[0].is_correct

        # One keyword missing -> half the points
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "Python is fun"})])
        assert result.results[0].total_points == 5.0
        assert not result.results[0].grade_details[0].is_correct

    def test_partial_mode_multiple_keywords(self):
        """Partial mode: multiple optional-like keywords awarded proportionally."""
        rule = KeywordRule(
            question_id="q1",
            keywords=["advanced", "expert", "professional"],
            mode="partial",
            max_points=6.0,
        )
        rubric = Rubric(name="Test", rules=[rule])

        result = grade(
            rubric,
            [Submission(student_id="s1", answers={"q1": "An advanced professional approach"})],
        )
        # 2 out of 3 keywords found -> 2/3 of 6 = 4.0
        assert result.results[0].total_points == 4.0

    def test_all_mode_requires_all_keywords(self):
        """All mode: full points only when every keyword is present."""
        rule = KeywordRule(
            question_id="q1",
            keywords=["a", "b", "c", "d"],
            mode="all",
            max_points=12.0,
        )
        rubric = Rubric(name="Test", rules=[rule])

        # All keywords present -> full points
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "a b c d"})])
        assert result.results[0].total_points == 12.0

        # Missing one -> zero points
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "a b c"})])
        assert result.results[0].total_points == 0.0

    def test_any_mode_awards_full_if_any_keyword_present(self):
        rule = KeywordRule(
            question_id="q1",
            keywords=["alpha", "beta", "gamma"],
            mode="any",
            max_points=9.0,
        )
        rubric = Rubric(name="Test", rules=[rule])

        # One keyword present -> full points
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "This mentions beta somewhere"})]
        )
        assert result.results[0].total_points == 9.0
        assert result.results[0].grade_details[0].is_correct

        # No keywords present -> zero points
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "No keywords here"})])
        assert result.results[0].total_points == 0.0
        assert not result.results[0].grade_details[0].is_correct


class TestKeywordSchemaValidation:
    """Test KeywordRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that KeywordRule validates correctly against TEXT schema."""
        rule = KeywordRule(
            question_id="q1",
            keywords=["python"],
            max_points=5.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": TextQuestionSchema(),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert errors == []

    def test_validate_incompatible_choice_schema(self):
        """Test that KeywordRule rejects CHOICE schema."""
        rule = KeywordRule(
            question_id="q1",
            keywords=["keyword"],
            max_points=5.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(options=["A", "B", "C"]),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "CHOICE" in errors[0]

    def test_validate_incompatible_numeric_schema(self):
        """Test that KeywordRule rejects NUMERIC schema."""
        rule = KeywordRule(
            question_id="q1",
            keywords=["keyword"],
            max_points=5.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": NumericQuestionSchema(),
            },
        )

        errors = rule.validate_against_schema("q1", schema.questions["q1"], "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "NUMERIC" in errors[0]
