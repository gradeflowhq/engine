"""
Tests for SimilarityRule grading logic.
"""

from gradeflow_engine import Rubric, SimilarityRule, Submission, grade
from gradeflow_engine.rules.similarity.model import SimilarityRuleConfig
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestSimilarityRule:
    """Test SimilarityRule grading logic."""

    def test_levenshtein_similarity(self):
        """Test Levenshtein distance similarity."""
        # Exact match should pass with threshold 0.8
        rule_exact = SimilarityRule(
            question_id="q1",
            reference="The quick brown fox",
            config=SimilarityRuleConfig(algorithm="levenshtein"),
            threshold=0.8,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule_exact])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "The quick brown fox"})])
        assert result.results[0].total_points == 10.0

        # Somewhat similar: use a lower threshold so similarity awards points (no partial credit)
        rule_somewhat = SimilarityRule(
            question_id="q1",
            reference="The quick brown fox",
            config=SimilarityRuleConfig(algorithm="levenshtein"),
            threshold=0.5,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule_somewhat])
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "The quick brown dog"})])
        assert result.results[0].total_points == 10.0

    def test_token_sort_similarity(self):
        """Test token sort similarity."""
        rule = SimilarityRule(
            question_id="q1",
            reference="brown fox quick",
            config=SimilarityRuleConfig(algorithm="token_sort"),
            threshold=0.9,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        # Same words, different order
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "quick brown fox"})])
        assert result.results[0].total_points == 10.0

    def test_jaro_winkler_similarity(self):
        """Test Jaro-Winkler similarity algorithm."""
        rule = SimilarityRule(
            question_id="q1",
            reference="hello world",
            config=SimilarityRuleConfig(algorithm="jaro_winkler"),
            threshold=0.8,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "hello worlld"})])
        assert result.results[0].total_points == 10.0

    def test_case_insensitive_similarity(self):
        """Test case-insensitive similarity matching."""
        # TextRuleConfig.ignore_case defaults to True, so omit or set explicitly
        rule = SimilarityRule(
            question_id="q1",
            reference="Python Programming",
            config=SimilarityRuleConfig(algorithm="levenshtein", ignore_case=True),
            threshold=0.95,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "python programming"})])
        assert result.results[0].total_points == 10.0

    def test_below_threshold(self):
        """Test answer below similarity threshold."""
        rule = SimilarityRule(
            question_id="q1",
            reference="correct answer",
            config=SimilarityRuleConfig(algorithm="levenshtein"),
            threshold=0.9,
            max_points=10.0,
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(
            rubric, [Submission(student_id="s1", answers={"q1": "completely different"})]
        )
        assert result.results[0].total_points == 0.0


class TestSimilaritySchemaValidation:
    """Test SimilarityRule schema validation."""

    def test_validate_against_text_schema(self):
        """Test that SimilarityRule validates correctly against TEXT schema."""
        rule = SimilarityRule(
            question_id="q1",
            reference="The answer",
            config=SimilarityRuleConfig(algorithm="levenshtein"),
            threshold=0.8,
            max_points=10.0,
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
        """Test that SimilarityRule rejects CHOICE schema."""
        rule = SimilarityRule(
            question_id="q1",
            reference="A",
            config=SimilarityRuleConfig(algorithm="levenshtein"),
            threshold=0.8,
            max_points=10.0,
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
        """Test that SimilarityRule rejects NUMERIC schema."""
        rule = SimilarityRule(
            question_id="q1",
            reference="42",
            config=SimilarityRuleConfig(algorithm="levenshtein"),
            threshold=0.8,
            max_points=10.0,
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
