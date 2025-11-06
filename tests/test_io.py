"""
Tests for I/O utilities (loading and saving rubrics and results).

Run with: pytest tests/test_io.py -v
"""

import csv

import pytest
import yaml

from gradeflow_engine import (
    ExactMatchRule,
    GradeDetail,
    GradeOutput,
    Rubric,
    StudentResult,
)
from gradeflow_engine.io import (
    export_canvas_csv,
    load_rubric,
    load_schema,
    load_submissions_csv,
    save_results_csv,
    save_results_yaml,
    save_rubric,
    save_schema,
)
from gradeflow_engine.schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema,
)


class TestLoadRubric:
    """Test rubric loading from YAML."""

    def test_load_valid_rubric(self, tmp_path):
        """Test loading a valid rubric YAML file."""
        yaml_file = tmp_path / "rubric.yaml"
        yaml_content = """
name: Test Rubric
rules:
  - type: EXACT_MATCH
    question_id: Q1
    answer: Paris
    max_points: 10.0
"""
        yaml_file.write_text(yaml_content)

        rubric = load_rubric(str(yaml_file))

        assert rubric.name == "Test Rubric"
        assert len(rubric.rules) == 1
        assert rubric.rules[0].type == "EXACT_MATCH"

    def test_load_nonexistent_file(self):
        """Test loading from a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_rubric("/nonexistent/path/rubric.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ValueError, match="Invalid YAML format"):
            load_rubric(str(yaml_file))

    def test_load_invalid_schema(self, tmp_path):
        """Test loading YAML that doesn't match rubric schema."""
        yaml_file = tmp_path / "invalid_schema.yaml"
        yaml_content = """
name: Test
rules:
  - type: INVALID_TYPE
    question_id: Q1
"""
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="Invalid rubric format"):
            load_rubric(str(yaml_file))


class TestSaveRubric:
    """Test rubric saving to YAML."""

    def test_save_rubric(self, tmp_path):
        """Test saving a rubric to YAML."""
        rubric = Rubric(
            name="Test Rubric",
            rules=[ExactMatchRule(question_id="Q1", answer="Paris", max_points=10.0)],
        )

        output_path = tmp_path / "rubric.yaml"
        save_rubric(rubric, str(output_path))

        assert output_path.exists()

        # Verify can be loaded back
        loaded = load_rubric(str(output_path))
        assert loaded.name == rubric.name
        assert len(loaded.rules) == 1


class TestLoadSubmissions:
    """Test loading submissions from CSV."""

    def test_load_valid_csv(self, tmp_path):
        """Test loading valid submissions CSV."""
        csv_path = tmp_path / "submissions.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["student_id", "Q1", "Q2"])
            writer.writerow(["student001", "A", "B"])
            writer.writerow(["student002", "C", "D"])

        submissions = load_submissions_csv(str(csv_path))

        assert len(submissions) == 2
        assert submissions[0].student_id == "student001"
        assert submissions[0].answers == {"Q1": "A", "Q2": "B"}
        assert submissions[1].student_id == "student002"

    def test_load_custom_student_col(self, tmp_path):
        """Test loading with custom student ID column name."""
        csv_path = tmp_path / "submissions.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "Q1"])
            writer.writerow(["user001", "A"])

        submissions = load_submissions_csv(str(csv_path), student_id_col="user_id")

        assert len(submissions) == 1
        assert submissions[0].student_id == "user001"

    def test_load_nonexistent_csv(self):
        """Test loading from nonexistent CSV."""
        with pytest.raises(FileNotFoundError):
            load_submissions_csv("/nonexistent/submissions.csv")

    def test_load_missing_student_col(self, tmp_path):
        """Test loading CSV without student ID column."""
        csv_path = tmp_path / "submissions.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Q1", "Q2"])
            writer.writerow(["A", "B"])

        with pytest.raises(ValueError, match="Student ID column"):
            load_submissions_csv(str(csv_path))


class TestSaveResults:
    """Test saving grading results."""

    @pytest.fixture
    def sample_results(self):
        """Create sample grading results."""
        return GradeOutput(
            results=[
                StudentResult(
                    student_id="student001",
                    total_points=85.0,
                    max_points=100.0,
                    percentage=85.0,
                    grade_details=[
                        GradeDetail(
                            question_id="Q1",
                            student_answer="Paris",
                            correct_answer="Paris",
                            points_awarded=10.0,
                            max_points=10.0,
                            is_correct=True,
                            feedback=None,
                        )
                    ],
                    metadata={},
                )
            ],
            metadata={"rubric_name": "Test"},
        )

    def test_save_results_yaml(self, sample_results, tmp_path):
        """Test saving results to YAML."""
        output_path = tmp_path / "results.yaml"
        save_results_yaml(sample_results, str(output_path))

        assert output_path.exists()

        # Verify content
        with open(output_path) as f:
            data = yaml.safe_load(f)
            assert len(data["results"]) == 1
            assert data["results"][0]["student_id"] == "student001"

    def test_save_results_csv_summary(self, sample_results, tmp_path):
        """Test saving summary CSV."""
        output_path = tmp_path / "summary.csv"
        save_results_csv(sample_results, str(output_path), include_details=False)

        assert output_path.exists()

        # Verify content
        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["student_id"] == "student001"
            assert rows[0]["total_points"] == "85.0"

    def test_save_results_csv_detailed(self, sample_results, tmp_path):
        """Test saving detailed CSV."""
        output_path = tmp_path / "detailed.csv"
        save_results_csv(sample_results, str(output_path), include_details=True)

        assert output_path.exists()

        # Verify content
        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["question_id"] == "Q1"
            assert rows[0]["is_correct"] == "True"

    def test_export_canvas_csv(self, sample_results, tmp_path):
        """Test exporting Canvas-compatible CSV."""
        output_path = tmp_path / "canvas.csv"
        export_canvas_csv(sample_results, str(output_path))

        assert output_path.exists()

        # Verify content
        with open(output_path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 2  # Header + 1 student
            assert rows[0][0] == "SIS User ID"
            assert rows[1][0] == "student001"
            assert rows[1][1] == "85.00"

    def test_export_canvas_csv_custom_assignment(self, sample_results, tmp_path):
        """Test Canvas export with custom assignment name."""
        output_path = tmp_path / "canvas.csv"
        export_canvas_csv(sample_results, str(output_path), assignment_name="Final Exam")

        with open(output_path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert rows[0][1] == "Final Exam"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_csv(self, tmp_path):
        """Test loading empty CSV."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        with pytest.raises(ValueError, match="empty"):
            load_submissions_csv(str(csv_file))

    def test_save_creates_directories(self, tmp_path):
        """Test that save functions create parent directories."""
        output_path = tmp_path / "subdir" / "nested" / "rubric.yaml"

        rubric = Rubric(name="Test", rules=[])
        save_rubric(rubric, str(output_path))

        assert output_path.exists()

    def test_load_rubric_invalid_yaml_format(self, tmp_path):
        """Test loading rubric with invalid YAML syntax."""
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("invalid: yaml: [[[")

        with pytest.raises(ValueError, match="Invalid YAML format"):
            load_rubric(str(yaml_file))

    def test_load_rubric_invalid_schema(self, tmp_path):
        """Test loading rubric with invalid schema."""
        yaml_file = tmp_path / "bad.yaml"
        yaml_content = """
name: Test
rules:
  - type: NONEXISTENT_RULE_TYPE
    question_id: Q1
"""
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="Invalid rubric format"):
            load_rubric(str(yaml_file))

    def test_load_submissions_validate_questions(self, tmp_path):
        """Test question validation when loading submissions."""
        csv_file = tmp_path / "subs.csv"
        csv_file.write_text("student_id,Q1,Q2\ns1,a1,a2\n")

        # Should raise error when Q3 is required but missing
        with pytest.raises(ValueError, match="missing required"):
            load_submissions_csv(str(csv_file), validate_questions=["Q1", "Q2", "Q3"])

    def test_load_submissions_missing_student_id_value(self, tmp_path):
        """Test CSV with empty student ID."""
        csv_file = tmp_path / "subs.csv"
        csv_file.write_text("student_id,Q1\n,answer1\n")

        with pytest.raises(ValueError, match="Missing student ID"):
            load_submissions_csv(str(csv_file))

    def test_export_canvas_default_assignment_name(self, tmp_path):
        """Test Canvas export with default assignment name from metadata."""
        csv_file = tmp_path / "canvas.csv"

        results = GradeOutput(
            results=[
                StudentResult(
                    student_id="s1",
                    total_points=85.0,
                    max_points=100.0,
                    percentage=85.0,
                    grade_details=[],
                )
            ],
            metadata={"rubric_name": "Quiz 1"},
        )

        export_canvas_csv(results, str(csv_file))

        with open(csv_file) as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header[1] == "Quiz 1"

    def test_export_canvas_no_metadata(self, tmp_path):
        """Test Canvas export with no metadata."""
        csv_file = tmp_path / "canvas.csv"

        results = GradeOutput(
            results=[
                StudentResult(
                    student_id="s1",
                    total_points=85.0,
                    max_points=100.0,
                    percentage=85.0,
                    grade_details=[],
                )
            ]
        )

        export_canvas_csv(results, str(csv_file))

        with open(csv_file) as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header[1] == "Assignment"  # Default name


class TestSchemaIO:
    """Test assessment schema loading and saving."""

    def test_save_and_load_schema(self, tmp_path):
        """Test saving and loading an assessment schema."""
        schema = AssessmentSchema(
            name="Test Assessment",
            questions={
                "q1": ChoiceQuestionSchema(
                    options=["A", "B", "C", "D"],
                    allow_multiple=False,
                ),
                "q2": NumericQuestionSchema(),
                "q3": TextQuestionSchema(),
            },
        )

        schema_file = tmp_path / "schema.yaml"
        save_schema(schema, str(schema_file))

        # Verify file was created
        assert schema_file.exists()

        # Load it back
        loaded_schema = load_schema(str(schema_file))

        # Verify contents
        assert loaded_schema.name == "Test Assessment"
        assert len(loaded_schema.questions) == 3
        assert "q1" in loaded_schema.questions
        assert "q2" in loaded_schema.questions
        assert "q3" in loaded_schema.questions

        # Verify question types
        assert loaded_schema.questions["q1"].type == "CHOICE"
        assert loaded_schema.questions["q2"].type == "NUMERIC"
        assert loaded_schema.questions["q3"].type == "TEXT"

        # Verify CHOICE question details
        q1 = loaded_schema.questions["q1"]
        assert isinstance(q1, ChoiceQuestionSchema)
        assert q1.options == ["A", "B", "C", "D"]
        assert q1.allow_multiple is False

        # Verify NUMERIC question details
        q2 = loaded_schema.questions["q2"]
        assert isinstance(q2, NumericQuestionSchema)

        # Verify TEXT question details
        q3 = loaded_schema.questions["q3"]
        assert isinstance(q3, TextQuestionSchema)

    def test_load_schema_with_metadata(self, tmp_path):
        """Test loading schema with metadata fields."""
        yaml_content = """
name: Quiz 1
metadata:
  course: CS101
  semester: Fall 2024
questions:
  q1:
    type: CHOICE
    question_id: q1
    options: ["True", "False"]
    allow_multiple: false
    metadata:
      points: 5
      difficulty: easy
"""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(yaml_content)

        schema = load_schema(str(schema_file))

        assert schema.name == "Quiz 1"
        assert schema.metadata["course"] == "CS101"
        assert schema.metadata["semester"] == "Fall 2024"
        assert schema.questions["q1"].metadata["points"] == 5
        assert schema.questions["q1"].metadata["difficulty"] == "easy"

    def test_load_schema_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        schema_file = tmp_path / "invalid.yaml"
        schema_file.write_text("invalid: yaml: [")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_schema(str(schema_file))

    def test_load_schema_missing_required_fields(self, tmp_path):
        """Test loading schema with missing required fields."""
        yaml_content = """
name: Test
questions:
  q1:
    type: CHOICE
    question_id: q1
    # Missing options field
"""
        schema_file = tmp_path / "invalid_schema.yaml"
        schema_file.write_text(yaml_content)

        with pytest.raises(Exception):  # noqa: B017 - Pydantic validation error
            load_schema(str(schema_file))

    def test_save_schema_with_all_question_types(self, tmp_path):
        """Test saving schema with all question types."""
        schema = AssessmentSchema(
            name="Comprehensive Test",
            questions={
                "choice_single": ChoiceQuestionSchema(
                    options=["Option A", "Option B"],
                    allow_multiple=False,
                ),
                "choice_multiple": ChoiceQuestionSchema(
                    options=["1", "2", "3", "4"],
                    allow_multiple=True,
                ),
                "numeric": NumericQuestionSchema(),
                "text": TextQuestionSchema(),
            },
        )

        schema_file = tmp_path / "comprehensive.yaml"
        save_schema(schema, str(schema_file))

        # Load and verify
        loaded = load_schema(str(schema_file))
        assert len(loaded.questions) == 4

        # Verify each question type
        assert loaded.questions["choice_single"].allow_multiple is False
        assert loaded.questions["choice_multiple"].allow_multiple is True
        assert loaded.questions["numeric"].type == "NUMERIC"
        assert loaded.questions["text"].type == "TEXT"

    def test_schema_file_not_found(self):
        """Test loading non-existent schema file."""
        with pytest.raises(FileNotFoundError):
            load_schema("/nonexistent/path/schema.yaml")
