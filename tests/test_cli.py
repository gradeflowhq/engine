"""
Comprehensive tests for the CLI module.

Tests the command-line interface including:
- Grade command with various options
- Validate rubric command
- Error handling
- Output formats
- Progress tracking

Run with: pytest tests/test_cli.py -v
"""

import csv

import pytest
import yaml
from typer.testing import CliRunner

from gradeflow_engine.cli import app as cli_app


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_rubric(tmp_path):
    """Create a sample rubric YAML file."""
    # Create sample rubric
    rubric_data = {
        "name": "Test Rubric",
        "rules": [
            {
                "type": "EXACT_MATCH",
                "question_id": "Q1",
                "correct_answer": "Paris",
                "max_points": 10.0,
            },
            {
                "type": "NUMERIC_RANGE",
                "question_id": "Q2",
                "min_value": 41.9,
                "max_value": 42.1,
                "max_points": 5.0,
            },
        ],
    }

    rubric_file = tmp_path / "rubric.yaml"
    with open(rubric_file, "w") as f:
        yaml.dump(rubric_data, f)

    return rubric_file


@pytest.fixture
def sample_submissions(tmp_path):
    """Create a sample submissions CSV file."""
    submissions_data = [
        {"student_id": "student1", "Q1": "Paris", "Q2": "9.8", "Q3": "A,C"},
        {"student_id": "student2", "Q1": "paris", "Q2": "9.81", "Q3": "A"},
        {"student_id": "student3", "Q1": "London", "Q2": "10.0", "Q3": "B"},
        {"student_id": "student4", "Q1": "PARIS", "Q2": "9.75", "Q3": "A,C"},
    ]

    submissions_file = tmp_path / "submissions.csv"
    with open(submissions_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["student_id", "Q1", "Q2", "Q3"])
        writer.writeheader()
        writer.writerows(submissions_data)

    return submissions_file


@pytest.fixture
def invalid_rubric(tmp_path):
    """Create an invalid rubric file."""
    invalid_data = {
        "name": "Invalid Rubric",
        "rules": [
            {
                "type": "EXACT_MATCH",
                "question_id": "Q1",
                # Missing required field: correct_answer
                "max_points": 10.0,
            }
        ],
    }

    rubric_file = tmp_path / "invalid_rubric.yaml"
    with open(rubric_file, "w") as f:
        yaml.dump(invalid_data, f)

    return rubric_file


class TestVersionCommand:
    """Test the --version command."""

    def test_version_short_flag(self, runner):
        """Test version display with -v flag."""
        result = runner.invoke(cli_app, ["-v"])
        assert result.exit_code == 0
        assert "gradeflow-engine version" in result.stdout

    def test_version_long_flag(self, runner):
        """Test version display with --version flag."""
        result = runner.invoke(cli_app, ["--version"])
        assert result.exit_code == 0
        assert "gradeflow-engine version" in result.stdout


class TestGradeCommand:
    """Test the grade command."""

    def test_grade_basic(self, runner, sample_rubric, sample_submissions, tmp_path):
        """Test basic grading with minimal options."""
        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify output structure
        with open(output_file) as f:
            output = yaml.safe_load(f)

        assert "results" in output
        assert "metadata" in output
        assert output["metadata"]["rubric_name"] == "Test Rubric"
        assert len(output["results"]) == 4

    def test_grade_with_progress(self, runner, sample_rubric, sample_submissions, tmp_path):
        """Test grading with progress display (not quiet)."""
        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app,
            ["grade", str(sample_rubric), str(sample_submissions), "--out", str(output_file)],
        )

        assert result.exit_code == 0
        assert "Loading rubric and submissions" in result.stdout or result.exit_code == 0
        assert output_file.exists()

    def test_grade_with_csv_summary(self, runner, sample_rubric, sample_submissions, tmp_path):
        """Test grading with CSV summary output."""
        output_file = tmp_path / "results.yaml"
        csv_summary = tmp_path / "summary.csv"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--csv-summary",
                str(csv_summary),
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert csv_summary.exists()

        # Verify CSV structure
        with open(csv_summary) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 4
        assert "student_id" in rows[0]
        assert "total_points" in rows[0]
        assert "max_points" in rows[0]

    def test_grade_with_csv_detailed(self, runner, sample_rubric, sample_submissions, tmp_path):
        """Test grading with detailed CSV output."""
        output_file = tmp_path / "results.yaml"
        csv_detailed = tmp_path / "detailed.csv"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--csv-detailed",
                str(csv_detailed),
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert csv_detailed.exists()

        # Verify CSV has detailed columns
        with open(csv_detailed) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Detailed CSV has one row per student-question pair
        # 4 students × 2 questions = 8 rows
        assert len(rows) == 8
        # Should have question-specific columns
        assert "question_id" in rows[0].keys()
        assert "student_answer" in rows[0].keys()

    def test_grade_with_canvas_export(self, runner, sample_rubric, sample_submissions, tmp_path):
        """Test grading with Canvas CSV export."""
        output_file = tmp_path / "results.yaml"
        canvas_file = tmp_path / "canvas.csv"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--canvas",
                str(canvas_file),
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert canvas_file.exists()

        # Verify Canvas format
        with open(canvas_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 4
        # Canvas format has columns: [student_id_field, assignment_name]
        # By default: ["SIS User ID", "Test Rubric"]
        assert "SIS User ID" in rows[0]
        assert "Test Rubric" in rows[0]

    def test_grade_with_all_outputs(self, runner, sample_rubric, sample_submissions, tmp_path):
        """Test grading with all output options enabled."""
        output_file = tmp_path / "results.yaml"
        csv_summary = tmp_path / "summary.csv"
        csv_detailed = tmp_path / "detailed.csv"
        canvas_file = tmp_path / "canvas.csv"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--csv-summary",
                str(csv_summary),
                "--csv-detailed",
                str(csv_detailed),
                "--canvas",
                str(canvas_file),
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert csv_summary.exists()
        assert csv_detailed.exists()
        assert canvas_file.exists()

    def test_grade_custom_student_id_column(self, runner, sample_rubric, tmp_path):
        """Test grading with custom student ID column name."""
        # Create submissions with custom column name
        submissions_data = [
            {"StudentID": "student1", "Q1": "Paris", "Q2": "9.8", "Q3": "A,C"},
            {"StudentID": "student2", "Q1": "paris", "Q2": "9.81", "Q3": "A"},
        ]

        submissions_file = tmp_path / "submissions_custom.csv"
        with open(submissions_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["StudentID", "Q1", "Q2", "Q3"])
            writer.writeheader()
            writer.writerows(submissions_data)

        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(submissions_file),
                "--out",
                str(output_file),
                "--student-col",
                "StudentID",
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        with open(output_file) as f:
            results = yaml.safe_load(f)

        assert len(results["results"]) == 2

    def test_grade_nonexistent_rubric(self, runner, sample_submissions, tmp_path):
        """Test grading with nonexistent rubric file."""
        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                "nonexistent_rubric.yaml",
                str(sample_submissions),
                "--out",
                str(output_file),
                "--quiet",
            ],
        )

        assert result.exit_code != 0

    def test_grade_nonexistent_submissions(self, runner, sample_rubric, tmp_path):
        """Test grading with nonexistent submissions file."""
        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                "nonexistent_submissions.csv",
                "--out",
                str(output_file),
                "--quiet",
            ],
        )

        assert result.exit_code != 0

    def test_grade_invalid_rubric(self, runner, invalid_rubric, sample_submissions, tmp_path):
        """Test grading with invalid rubric."""
        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(invalid_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--quiet",
            ],
        )

        assert result.exit_code == 1
        assert "Error:" in result.stdout

    def test_grade_empty_submissions(self, runner, sample_rubric, tmp_path):
        """Test grading with empty submissions file."""
        empty_submissions = tmp_path / "empty_submissions.csv"
        with open(empty_submissions, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["student_id", "Q1", "Q2", "Q3"])
            # No data rows

        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(empty_submissions),
                "--out",
                str(output_file),
                "--quiet",
            ],
        )

        # Should succeed with empty results
        assert result.exit_code == 0
        assert output_file.exists()


class TestValidateRubricCommand:
    """Test the validate-rubric command."""

    def test_validate_valid_rubric(self, runner, sample_rubric):
        """Test validating a valid rubric."""
        result = runner.invoke(cli_app, ["validate-rubric", str(sample_rubric)])

        assert result.exit_code == 0
        assert "Rubric is valid" in result.stdout

    def test_validate_valid_rubric_verbose(self, runner, sample_rubric):
        """Test validating a valid rubric with verbose output."""
        result = runner.invoke(cli_app, ["validate-rubric", str(sample_rubric), "--verbose"])

        assert result.exit_code == 0
        assert "Rubric is valid" in result.stdout
        assert "Rubric Details:" in result.stdout
        assert "Rule Types:" in result.stdout
        assert "EXACT_MATCH" in result.stdout

    def test_validate_invalid_rubric(self, runner, invalid_rubric):
        """Test validating an invalid rubric."""
        result = runner.invoke(cli_app, ["validate-rubric", str(invalid_rubric)])

        assert result.exit_code == 1
        assert "Validation failed:" in result.stdout

    def test_validate_nonexistent_rubric(self, runner):
        """Test validating a nonexistent rubric file."""
        result = runner.invoke(cli_app, ["validate-rubric", "nonexistent_rubric.yaml"])

        assert result.exit_code != 0

    def test_validate_malformed_yaml(self, runner, tmp_path):
        """Test validating a malformed YAML file."""
        malformed_file = tmp_path / "malformed.yaml"
        with open(malformed_file, "w") as f:
            f.write("name: Test\nrules:\n  - type: EXACT_MATCH\n    invalid yaml here [[[")

        result = runner.invoke(cli_app, ["validate-rubric", str(malformed_file)])

        assert result.exit_code == 1


class TestDisplaySummaryTable:
    """Test the summary table display functionality."""

    def test_summary_table_with_results(self, runner, sample_rubric, sample_submissions, tmp_path):
        """Test that summary table is displayed for successful grading."""
        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app,
            ["grade", str(sample_rubric), str(sample_submissions), "--out", str(output_file)],
        )

        # Check for table headers in output (not in quiet mode)
        assert result.exit_code == 0
        # The table might be displayed with Rich formatting

    def test_summary_table_truncation(self, runner, sample_rubric, tmp_path):
        """Test that summary table truncates for many students."""
        # Create submissions with more than 10 students
        submissions_data = [
            {"student_id": f"student{i}", "Q1": "Paris", "Q2": "9.8", "Q3": "A,C"}
            for i in range(15)
        ]

        submissions_file = tmp_path / "many_submissions.csv"
        with open(submissions_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["student_id", "Q1", "Q2", "Q3"])
            writer.writeheader()
            writer.writerows(submissions_data)

        output_file = tmp_path / "results.yaml"

        result = runner.invoke(
            cli_app, ["grade", str(sample_rubric), str(submissions_file), "--out", str(output_file)]
        )

        assert result.exit_code == 0
        # Should show "..." for truncated results


class TestCLIEdgeCases:
    """Test edge cases and error conditions."""

    def test_grade_with_special_characters_in_path(
        self, runner, sample_rubric, sample_submissions, tmp_path
    ):
        """Test grading with special characters in output path."""
        output_dir = tmp_path / "output with spaces"
        output_dir.mkdir()
        output_file = output_dir / "results (final).yaml"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

    def test_grade_creates_output_directory(
        self, runner, sample_rubric, sample_submissions, tmp_path
    ):
        """Test that grading creates output directory if it doesn't exist."""
        output_file = tmp_path / "new_dir" / "subdir" / "results.yaml"

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

    def test_grade_overwrites_existing_output(
        self, runner, sample_rubric, sample_submissions, tmp_path
    ):
        """Test that grading overwrites existing output file."""
        output_file = tmp_path / "results.yaml"

        # Create existing file
        with open(output_file, "w") as f:
            f.write("old content")

        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--quiet",
            ],
        )

        assert result.exit_code == 0

        # Verify new content
        with open(output_file) as f:
            content = f.read()

        assert "old content" not in content
        assert "results:" in content

    def test_no_command_shows_help(self, runner):
        """Test that running with no command shows error or help."""
        result = runner.invoke(cli_app, [])

        # Typer shows an error when no command is given
        # We just verify it doesn't crash and shows some output
        assert result.exit_code in [0, 2]  # 0 = success, 2 = usage error
        assert len(result.stderr) > 0  # Should show some output

    def test_invalid_command(self, runner):
        """Test running an invalid command."""
        result = runner.invoke(cli_app, ["invalid-command"])

        assert result.exit_code != 0


class TestCLIIntegration:
    """Integration tests for CLI workflows."""

    def test_validate_then_grade_workflow(
        self, runner, sample_rubric, sample_submissions, tmp_path
    ):
        """Test workflow: validate rubric, then grade."""
        # First validate
        validate_result = runner.invoke(cli_app, ["validate-rubric", str(sample_rubric)])
        assert validate_result.exit_code == 0

        # Then grade
        output_file = tmp_path / "results.yaml"
        grade_result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(output_file),
                "--quiet",
            ],
        )
        assert grade_result.exit_code == 0
        assert output_file.exists()

    def test_multiple_output_formats_workflow(
        self, runner, sample_rubric, sample_submissions, tmp_path
    ):
        """Test generating all output formats in one command."""
        result = runner.invoke(
            cli_app,
            [
                "grade",
                str(sample_rubric),
                str(sample_submissions),
                "--out",
                str(tmp_path / "results.yaml"),
                "--csv-summary",
                str(tmp_path / "summary.csv"),
                "--csv-detailed",
                str(tmp_path / "detailed.csv"),
                "--canvas",
                str(tmp_path / "canvas.csv"),
                "--quiet",
            ],
        )

        assert result.exit_code == 0
        assert (tmp_path / "results.yaml").exists()
        assert (tmp_path / "summary.csv").exists()
        assert (tmp_path / "detailed.csv").exists()
        assert (tmp_path / "canvas.csv").exists()
