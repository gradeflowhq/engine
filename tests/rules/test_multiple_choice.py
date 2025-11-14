"""
Tests for MultipleChoiceRule grading logic.
"""

from gradeflow_engine import MultipleChoiceRule, Rubric, Submission, grade

# Add explicit config model import for proper config objects
from gradeflow_engine.rules.multiple_choice.model import MultipleChoiceRuleConfig
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestMultipleChoiceRule:
    """Test MultipleChoiceRule grading logic."""

    def test_all_or_nothing_single_correct(self):
        """Test all-or-nothing with single correct answer."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["b"],  # use lowercase to match current validation behavior
            max_points=10.0,
            mode="all",
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "B"})])
        assert result.results[0].total_points == 10.0

        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "A"})])
        assert result.results[0].total_points == 0.0

    def test_all_or_nothing_multiple_correct(self):
        """Test all-or-nothing with multiple correct answers."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["a", "c"],
            max_points=10.0,
            mode="all",
        )
        rubric = Rubric(name="Test", rules=[rule])
        # All correct
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A,C"})])
        assert result.results[0].total_points == 10.0

        # Partial
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "A"})])
        assert result.results[0].total_points == 0.0

    def test_partial_scoring(self):
        """Test partial credit scoring."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["a", "b", "c"],
            max_points=12.0,
            mode="partial",
        )
        rubric = Rubric(name="Test", rules=[rule])
        # All correct
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A,B,C"})])
        assert result.results[0].total_points == 12.0

        # 2 out of 3
        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "A,B"})])
        assert result.results[0].total_points == 8.0

        # 1 out of 3
        result = grade(rubric, [Submission(student_id="s3", answers={"q1": "C"})])
        assert result.results[0].total_points == 4.0

    def test_custom_delimiter(self):
        """Test custom delimiter for answers."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["a", "c"],
            max_points=10.0,
            mode="all",
            config=MultipleChoiceRuleConfig(delimiter=";"),
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A;C"})])
        assert result.results[0].total_points == 10.0

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["a", "b"],
            max_points=10.0,
            mode="all",
            config=MultipleChoiceRuleConfig(trim_whitespace=True),
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": " A , B "})])
        assert result.results[0].total_points == 10.0

    def test_case_sensitivity(self):
        """Test case-sensitive matching."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["a"],
            max_points=10.0,
            mode="all",
            config=MultipleChoiceRuleConfig(ignore_case=False),
        )
        rubric = Rubric(name="Test", rules=[rule])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "A"})])
        assert result.results[0].total_points == 0.0

        result = grade(rubric, [Submission(student_id="s2", answers={"q1": "a"})])
        assert result.results[0].total_points == 10.0


class TestMultipleChoiceSchemaValidation:
    """Test MultipleChoiceRule schema validation."""

    def test_validate_against_choice_schema(self):
        """Test that MultipleChoiceRule validates correctly against CHOICE schema."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["a", "b"],  # lowercase to align with current validation implementation
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(options=["A", "B", "C", "D"]),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert errors == []

    def test_validate_incompatible_numeric_schema(self):
        """Test that MultipleChoiceRule rejects NUMERIC schema."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["a"],
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": NumericQuestionSchema(),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "CHOICE" in errors[0]

    def test_validate_incompatible_text_schema(self):
        """Test that MultipleChoiceRule rejects TEXT schema."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["answer"],
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": TextQuestionSchema(),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert len(errors) == 1
        assert "only compatible with" in errors[0]

    def test_validate_answer_not_in_options(self):
        """Test that MultipleChoiceRule validates answers are in schema options."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["a", "e"],  # 'e' not in options; lowercase to match validation
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(options=["A", "B", "C", "D"]),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert len(errors) == 1
        assert "not in schema options" in errors[0]
        assert "e" in errors[0]

    def test_validate_multiple_answers_not_in_options(self):
        """Test validation with multiple invalid answers."""
        rule = MultipleChoiceRule(
            question_id="q1",
            answers=["e", "f"],  # Both not in options
            max_points=10.0,
        )
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(options=["A", "B", "C"]),
            },
        )

        errors = rule.validate_against_question_schema(schema.questions, "Rule 1")
        assert len(errors) >= 1
        assert "not in schema options" in errors[0]
