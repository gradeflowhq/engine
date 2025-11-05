"""
Tests for RegexRule grading logic.
"""

from gradeflow_engine import RegexRule, Rubric, Submission, grade
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestRegexRule:
    """Test RegexRule grading logic."""

    def test_all_patterns_match(self):
        """Test 'all' match mode - all patterns must match."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"\d+", r"[A-Z]"],
            points_per_match=5.0,
            match_mode="all",
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Both patterns match - should get max_points = 5.0 * 2 = 10.0
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "ABC 123"})])
        assert result.results[0].total_points == 10.0

        # Only one pattern matches - partial credit or 0 depending on partial_credit flag
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "123"})])
        # With partial_credit=True (default), should get 5.0 (1 out of 2 patterns)
        assert result.results[0].total_points == 5.0

    def test_any_pattern_match(self):
        """Test 'any' match mode - any pattern match awards points."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"\d+", r"[A-Z]"],
            points_per_match=5.0,
            match_mode="any",
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Only one pattern matches
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "123"})])
        assert result.results[0].total_points == 5.0

    def test_count_matches(self):
        """Test 'count' mode - award points per pattern matched."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"cat", r"dog", r"bird"],
            points_per_match=3.0,
            match_mode="count",
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "I have a cat and a dog"})]
        )
        assert result.results[0].total_points == 6.0  # 2 patterns matched

    def test_case_insensitive(self):
        """Test case-insensitive regex matching."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"python"],
            points_per_match=10.0,
            match_mode="all",
            case_sensitive=False,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "I love PYTHON"})])
        assert result.results[0].total_points == 10.0

    def test_multiline_mode(self):
        """Test multiline and dotall flags."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"^Start.*End$"],
            points_per_match=10.0,
            match_mode="all",
            multiline=True,
            dotall=True,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Start\nmiddle\nEnd"})])
        assert result.results[0].total_points == 10.0

    def test_no_partial_credit(self):
        """Test with partial credit disabled."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"\d+", r"[A-Z]+"],
            points_per_match=5.0,
            match_mode="all",
            partial_credit=False,
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Only one pattern matches, partial_credit=False means 0 points
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "123"})])
        assert result.results[0].total_points == 0.0


class TestRegexSchemaValidation:
    """Test RegexRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that RegexRule validates correctly against TEXT schema."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"\d+"],
            points_per_match=10.0,
            match_mode="all",
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
        """Test that RegexRule rejects CHOICE schema."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"[A-Z]"],
            points_per_match=10.0,
            match_mode="all",
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
        """Test that RegexRule rejects NUMERIC schema."""
        rule = RegexRule(
            question_id="q1",
            patterns=[r"\d+"],
            points_per_match=10.0,
            match_mode="all",
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
