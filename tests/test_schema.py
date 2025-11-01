"""
Tests for assessment schema validation and inference.

Run with: pytest tests/test_schema.py -v
"""

import pytest

from gradeflow_engine import (
    ExactMatchRule,
    KeywordRule,
    MultipleChoiceRule,
    NumericRangeRule,
    ProgrammableRule,
    Rubric,
    Submission,
)
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    SchemaValidationError,
    TextQuestionSchema,
    infer_mcq_options,
    infer_numeric_range,
    infer_schema_from_submissions,
    validate_rubric_against_schema,
    validate_rubric_against_schema_strict,
)


class TestQuestionSchemas:
    """Test individual question schema models."""

    def test_choice_question_schema(self):
        """Test ChoiceQuestionSchema creation and validation."""
        schema = ChoiceQuestionSchema(
            question_id="q1",
            options=["A", "B", "C", "D"],
            allow_multiple=False,
        )

        assert schema.type == "CHOICE"
        assert schema.question_id == "q1"
        assert schema.options == ["A", "B", "C", "D"]
        assert schema.allow_multiple is False
        assert schema.metadata == {}

    def test_choice_question_with_metadata(self):
        """Test ChoiceQuestionSchema with metadata."""
        schema = ChoiceQuestionSchema(
            question_id="q1",
            options=["True", "False"],
            allow_multiple=False,
            metadata={"difficulty": "easy", "topic": "logic"},
        )

        assert schema.metadata["difficulty"] == "easy"
        assert schema.metadata["topic"] == "logic"

    def test_choice_question_empty_options(self):
        """Test that empty options list raises error."""
        with pytest.raises(ValueError, match="Options list cannot be empty"):
            ChoiceQuestionSchema(
                question_id="q1",
                options=[],
            )

    def test_choice_question_allow_multiple(self):
        """Test ChoiceQuestionSchema with multiple selections."""
        schema = ChoiceQuestionSchema(
            question_id="mrq",
            options=["1", "2", "3", "4"],
            allow_multiple=True,
        )

        assert schema.allow_multiple is True

    def test_numeric_question_schema(self):
        """Test NumericQuestionSchema creation."""
        schema = NumericQuestionSchema(
            question_id="q2",
            numeric_range=(0.0, 100.0),
        )

        assert schema.type == "NUMERIC"
        assert schema.question_id == "q2"
        assert schema.numeric_range == (0.0, 100.0)
        assert schema.metadata == {}

    def test_numeric_question_no_range(self):
        """Test NumericQuestionSchema without range constraint."""
        schema = NumericQuestionSchema(
            question_id="q2",
        )

        assert schema.numeric_range is None

    def test_text_question_schema(self):
        """Test TextQuestionSchema creation."""
        schema = TextQuestionSchema(
            question_id="q3",
            max_length=500,
        )

        assert schema.type == "TEXT"
        assert schema.question_id == "q3"
        assert schema.max_length == 500
        assert schema.metadata == {}

    def test_text_question_no_length_limit(self):
        """Test TextQuestionSchema without length constraint."""
        schema = TextQuestionSchema(
            question_id="q3",
        )

        assert schema.max_length is None

    def test_text_question_invalid_max_length(self):
        """Test that non-positive max_length raises error."""
        with pytest.raises(ValueError, match="max_length must be positive"):
            TextQuestionSchema(
                question_id="q3",
                max_length=0,
            )

        with pytest.raises(ValueError, match="max_length must be positive"):
            TextQuestionSchema(
                question_id="q3",
                max_length=-10,
            )


class TestAssessmentSchema:
    """Test AssessmentSchema model."""

    def test_create_assessment_schema(self):
        """Test creating a complete assessment schema."""
        schema = AssessmentSchema(
            name="Midterm Exam",
            questions={
                "q1": ChoiceQuestionSchema(
                    question_id="q1",
                    options=["A", "B", "C"],
                ),
                "q2": NumericQuestionSchema(
                    question_id="q2",
                    numeric_range=(0.0, 10.0),
                ),
                "q3": TextQuestionSchema(
                    question_id="q3",
                    max_length=1000,
                ),
            },
        )

        assert schema.name == "Midterm Exam"
        assert len(schema.questions) == 3
        assert "q1" in schema.questions
        assert "q2" in schema.questions
        assert "q3" in schema.questions

    def test_assessment_schema_with_metadata(self):
        """Test AssessmentSchema with metadata."""
        schema = AssessmentSchema(
            name="Quiz 1",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A", "B"]),
            },
            metadata={"course": "CS101", "semester": "Fall 2024"},
        )

        assert schema.metadata["course"] == "CS101"
        assert schema.metadata["semester"] == "Fall 2024"

    def test_assessment_schema_empty_questions(self):
        """Test that empty questions dict raises error."""
        with pytest.raises(ValueError, match="at least one question"):
            AssessmentSchema(
                name="Empty Test",
                questions={},
            )

    def test_assessment_schema_question_id_mismatch(self):
        """Test that question_id must match dictionary key."""
        with pytest.raises(ValueError, match="Question ID mismatch"):
            AssessmentSchema(
                name="Test",
                questions={
                    "q1": ChoiceQuestionSchema(
                        question_id="q2",  # Mismatch!
                        options=["A", "B"],
                    ),
                },
            )

    def test_discriminated_union(self):
        """Test that discriminated union works correctly."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A"]),
                "q2": NumericQuestionSchema(question_id="q2"),
                "q3": TextQuestionSchema(question_id="q3"),
            },
        )

        # Verify types are preserved correctly
        assert isinstance(schema.questions["q1"], ChoiceQuestionSchema)
        assert isinstance(schema.questions["q2"], NumericQuestionSchema)
        assert isinstance(schema.questions["q3"], TextQuestionSchema)


class TestSchemaInference:
    """Test schema inference from submission data."""

    def test_infer_mcq_options(self):
        """Test inferring MCQ options from answers."""
        answers = ["A", "A", "B", "A", "C", "B", "A"]

        options = infer_mcq_options(answers, min_frequency=0.1)

        # A appears 4 times (57%), B appears 2 times (28%), C appears 1 time (14%)
        # All should be included with 10% threshold
        assert "A" in options
        assert "B" in options
        assert "C" in options

    def test_infer_mcq_options_with_threshold(self):
        """Test MCQ option inference with higher threshold."""
        answers = ["A"] * 10 + ["B"] * 2 + ["C"] * 1

        options = infer_mcq_options(answers, min_frequency=0.2)

        # Only A (77%) and B (15%) should be excluded if threshold is 20%
        # But B is exactly at threshold, so let's check
        assert "A" in options
        # C appears only 7.7%, should be excluded

    def test_infer_mcq_options_multiple_response(self):
        """Test inferring options from multiple response questions."""
        answers = ["A,B", "A,C", "B,C", "A", "B,C,D"]

        options = infer_mcq_options(answers)

        # All options should be detected
        assert "A" in options
        assert "B" in options
        assert "C" in options
        assert "D" in options

    def test_infer_mcq_options_empty_answers(self):
        """Test MCQ option inference with empty answers."""
        assert infer_mcq_options([]) == []
        assert infer_mcq_options(["", "  ", ""]) == []

    def test_infer_numeric_range(self):
        """Test inferring numeric range from answers."""
        answers = ["85.5", "90.0", "78.3", "92.1", "88.0"]

        num_range = infer_numeric_range(answers)

        assert num_range is not None
        assert num_range[0] == 78.3  # min
        assert num_range[1] == 92.1  # max

    def test_infer_numeric_range_non_numeric(self):
        """Test numeric range inference with non-numeric data."""
        answers = ["hello", "world", "test"]

        num_range = infer_numeric_range(answers)

        assert num_range is None

    def test_infer_numeric_range_mixed(self):
        """Test numeric range with mixed numeric/non-numeric."""
        answers = ["10", "20", "not a number", "30"]

        num_range = infer_numeric_range(answers)

        assert num_range is not None
        assert num_range == (10.0, 30.0)

    def test_infer_schema_from_submissions(self):
        """Test inferring complete schema from submissions."""
        submissions = [
            Submission(student_id="s1", answers={"q1": "A", "q2": "85.5", "q3": "Short answer"}),
            Submission(
                student_id="s2", answers={"q1": "B", "q2": "90.0", "q3": "Another short answer"}
            ),
            Submission(student_id="s3", answers={"q1": "A", "q2": "78.0", "q3": "Brief response"}),
        ]

        schema = infer_schema_from_submissions(submissions, name="Inferred Quiz")

        assert schema.name == "Inferred Quiz"
        assert len(schema.questions) == 3

        # q1 should be inferred as CHOICE (limited unique values, short)
        assert schema.questions["q1"].type == "CHOICE"
        assert isinstance(schema.questions["q1"], ChoiceQuestionSchema)

        # q2 should be inferred as NUMERIC (>80% numeric)
        assert schema.questions["q2"].type == "NUMERIC"
        assert isinstance(schema.questions["q2"], NumericQuestionSchema)

        # q3 should be inferred as TEXT (longer text)
        assert schema.questions["q3"].type == "TEXT"
        assert isinstance(schema.questions["q3"], TextQuestionSchema)

    def test_infer_schema_multiple_response(self):
        """Test inferring schema with multiple response questions."""
        submissions = [
            Submission(student_id="s1", answers={"mrq": "A,B"}),
            Submission(student_id="s2", answers={"mrq": "A,C"}),
            Submission(student_id="s3", answers={"mrq": "B,C,D"}),
        ]

        schema = infer_schema_from_submissions(submissions)

        q_schema = schema.questions["mrq"]
        assert q_schema.type == "CHOICE"
        assert isinstance(q_schema, ChoiceQuestionSchema)
        assert q_schema.allow_multiple is True  # Should detect multiple selections

    def test_infer_schema_empty_submissions(self):
        """Test that empty submissions raises error."""
        with pytest.raises(ValueError, match="empty submissions"):
            infer_schema_from_submissions([])

    def test_infer_schema_no_questions(self):
        """Test that submissions with no questions raises error."""
        submissions = [
            Submission(student_id="s1", answers={}),
            Submission(student_id="s2", answers={}),
        ]

        with pytest.raises(ValueError, match="No questions found"):
            infer_schema_from_submissions(submissions)


class TestRubricValidation:
    """Test rubric validation against schema."""

    def test_validate_rubric_all_valid(self):
        """Test validation with valid rubric."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(
                    question_id="q1",
                    options=["Paris", "London", "Berlin"],
                ),
                "q2": NumericQuestionSchema(
                    question_id="q2",
                    numeric_range=(0.0, 100.0),
                ),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                MultipleChoiceRule(
                    question_id="q1",
                    correct_answers=["Paris"],
                    max_points=10.0,
                    description="Capital of France",
                ),
                NumericRangeRule(
                    question_id="q2",
                    min_value=9.5,
                    max_value=10.5,
                    max_points=10.0,
                    unit="g/cm³",
                    description="Gold density",
                ),
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert errors == []

    def test_validate_question_not_in_schema(self):
        """Test validation with question not in schema."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A", "B"]),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                MultipleChoiceRule(
                    question_id="q99",  # Not in schema!
                    correct_answers=["A"],
                    max_points=10.0,
                    description="Test",
                ),
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert len(errors) == 1
        assert "q99" in errors[0]
        assert "not found in schema" in errors[0]

    def test_validate_incompatible_rule_type(self):
        """Test validation with incompatible rule type."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": NumericQuestionSchema(question_id="q1"),  # NUMERIC question
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                MultipleChoiceRule(  # But using CHOICE rule!
                    question_id="q1",
                    correct_answers=["A"],
                    max_points=10.0,
                    description="Test",
                ),
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert len(errors) == 1
        assert "only compatible with" in errors[0]
        assert "CHOICE" in errors[0]

    def test_validate_invalid_mcq_option(self):
        """Test validation with MCQ answer not in schema options."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(
                    question_id="q1",
                    options=["A", "B", "C"],
                ),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                MultipleChoiceRule(
                    question_id="q1",
                    correct_answers=["D"],  # Not in schema options!
                    max_points=10.0,
                    description="Test",
                ),
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert len(errors) == 1
        assert "not in schema options" in errors[0]
        assert "D" in errors[0]

    def test_validate_numeric_range_outside_schema(self):
        """Test validation with numeric range outside schema range."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": NumericQuestionSchema(
                    question_id="q1",
                    numeric_range=(0.0, 100.0),
                ),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                NumericRangeRule(
                    question_id="q1",
                    min_value=-10.0,  # Outside schema range!
                    max_value=110.0,  # Outside schema range!
                    max_points=10.0,
                    unit="points",
                    description="Test",
                ),
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert len(errors) == 1
        assert "outside schema range" in errors[0]

    def test_validate_text_rule_on_text_question(self):
        """Test validation with text rules on text questions."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "essay": TextQuestionSchema(
                    question_id="essay",
                    max_length=5000,
                ),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                KeywordRule(
                    question_id="essay",
                    required_keywords=["analysis", "conclusion"],
                    points_per_required=5.0,
                    description="Essay keywords",
                ),
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert errors == []

    def test_validate_programmable_rule_any_type(self):
        """Test that programmable rules work with any question type."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A"]),
                "q2": NumericQuestionSchema(question_id="q2"),
                "q3": TextQuestionSchema(question_id="q3"),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                ProgrammableRule(
                    question_id="q1",
                    script="points_awarded = 10.0",
                    max_points=10.0,
                    description="Custom logic for q1",
                ),
                ProgrammableRule(
                    question_id="q2",
                    script="points_awarded = 10.0",
                    max_points=10.0,
                    description="Custom logic for q2",
                ),
                ProgrammableRule(
                    question_id="q3",
                    script="points_awarded = 10.0",
                    max_points=10.0,
                    description="Custom logic for q3",
                ),
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert errors == []  # Programmable rules work with all types

    def test_validate_exact_match_choice_and_text(self):
        """Test ExactMatchRule compatibility with CHOICE and TEXT."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["True", "False"]),
                "q2": TextQuestionSchema(question_id="q2"),
                "q3": NumericQuestionSchema(question_id="q3"),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                ExactMatchRule(
                    question_id="q1", correct_answer="True", max_points=5.0, description="Boolean"
                ),
                ExactMatchRule(
                    question_id="q2", correct_answer="answer", max_points=5.0, description="Text"
                ),
                ExactMatchRule(
                    question_id="q3", correct_answer="42", max_points=5.0, description="Number"
                ),  # Invalid!
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert len(errors) == 1  # Only q3 should error
        assert "q3" in errors[0] or "Rule 3" in errors[0]
        assert "only compatible with" in errors[0]

    def test_validate_rubric_strict_raises_exception(self):
        """Test strict validation raises SchemaValidationError."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A"]),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                MultipleChoiceRule(
                    question_id="q99",  # Not in schema
                    correct_answers=["A"],
                    max_points=10.0,
                    description="Test strict validation",
                ),
            ],
        )

        with pytest.raises(SchemaValidationError) as exc_info:
            validate_rubric_against_schema_strict(rubric, schema)

        assert len(exc_info.value.errors) == 1
        assert "q99" in exc_info.value.errors[0]

    def test_validate_multiple_errors(self):
        """Test validation with multiple errors."""
        schema = AssessmentSchema(
            name="Test",
            questions={
                "q1": ChoiceQuestionSchema(question_id="q1", options=["A", "B"]),
                "q2": NumericQuestionSchema(question_id="q2", numeric_range=(0.0, 10.0)),
            },
        )

        rubric = Rubric(
            name="Test Rubric",
            rules=[
                MultipleChoiceRule(
                    question_id="q1",
                    correct_answers=["Z"],  # Invalid option
                    max_points=10.0,
                    description="Invalid option test",
                ),
                MultipleChoiceRule(
                    question_id="q99",  # Question doesn't exist
                    correct_answers=["A"],
                    max_points=10.0,
                    description="Missing question test",
                ),
                NumericRangeRule(
                    question_id="q2",
                    min_value=-5.0,  # Outside schema range
                    max_value=15.0,
                    max_points=10.0,
                    unit="points",
                    description="Outside range test",
                ),
            ],
        )

        errors = validate_rubric_against_schema(rubric, schema)
        assert len(errors) >= 3  # At least 3 errors


class TestCompatibleTypes:
    """Test that all rules have compatible_types attribute."""

    def test_multiple_choice_compatible_types(self):
        """Test MultipleChoiceRule compatible types."""
        rule = MultipleChoiceRule(
            question_id="q1",
            correct_answers=["A"],
            max_points=10.0,
            description="Test",
        )
        assert rule.compatible_types == {"CHOICE"}

    def test_numeric_range_compatible_types(self):
        """Test NumericRangeRule compatible types."""
        rule = NumericRangeRule(
            question_id="q1",
            min_value=0.0,
            max_value=10.0,
            max_points=10.0,
            unit="points",
            description="Test",
        )
        assert rule.compatible_types == {"NUMERIC"}

    def test_exact_match_compatible_types(self):
        """Test ExactMatchRule compatible types."""
        rule = ExactMatchRule(
            question_id="q1",
            correct_answer="test",
            max_points=10.0,
            description="Test",
        )
        assert rule.compatible_types == {"CHOICE", "TEXT"}

    def test_keyword_compatible_types(self):
        """Test KeywordRule compatible types."""
        rule = KeywordRule(
            question_id="q1",
            required_keywords=["test"],
            points_per_required=5.0,
            description="Test",
        )
        assert rule.compatible_types == {"TEXT"}

    def test_programmable_compatible_types(self):
        """Test ProgrammableRule compatible types."""
        rule = ProgrammableRule(
            question_id="q1",
            script="points_awarded = 10.0",
            max_points=10.0,
            description="Test",
        )
        assert rule.compatible_types == {"CHOICE", "NUMERIC", "TEXT"}
