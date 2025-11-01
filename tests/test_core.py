"""
Tests for core grading functionality.

Run with: pytest tests/test_core.py -v
"""

import csv

import pytest
from pydantic import ValidationError

from gradeflow_engine import (
    ExactMatchRule,
    LengthRule,
    NumericRangeRule,
    Rubric,
    Submission,
    grade,
    grade_from_files,
)
from gradeflow_engine.io import save_rubric


def save_submissions_to_csv(submissions, file_path):
    """Helper to save submissions to CSV."""
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        if not submissions:
            writer = csv.writer(f)
            writer.writerow(["student_id"])
            return

        # Get all question IDs
        all_questions = set()
        for sub in submissions:
            all_questions.update(sub.answers.keys())

        fieldnames = ["student_id"] + sorted(all_questions)
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for sub in submissions:
            row = {"student_id": sub.student_id}
            row.update(sub.answers)
            writer.writerow(row)


class TestGradeFunction:
    """Test the main grade() function."""

    def test_grade_simple(self):
        """Test simple grading."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(
                    question_id="Q1", correct_answer="A", max_points=10, description="Test"
                )
            ],
        )
        submissions = [
            Submission(student_id="s1", answers={"Q1": "A"}),
            Submission(student_id="s2", answers={"Q1": "B"}),
        ]
        result = grade(rubric, submissions)
        assert len(result.results) == 2
        assert result.results[0].total_points == 10
        assert result.results[1].total_points == 0

    def test_grade_multiple_rules_same_question(self):
        """Test multiple rules grading the same question."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(
                    question_id="Q1", correct_answer="A", max_points=5, description="Test"
                ),
                NumericRangeRule(
                    question_id="Q1",
                    min_value=9.0,
                    max_value=11.0,
                    max_points=5,
                    description="Test",
                ),
            ],
        )
        submission = Submission(student_id="s1", answers={"Q1": "10"})

        result = grade(rubric, [submission])
        # Should get points from the numeric rule
        assert result.results[0].total_points > 0


class TestGradeFromFiles:
    """Test grade_from_files() function."""

    def test_grade_from_files_basic(self, tmp_path):
        """Test grading from files with basic setup."""
        # Create rubric file
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(
                    question_id="Q1", correct_answer="A", max_points=10, description="Test"
                )
            ],
        )
        rubric_path = tmp_path / "rubric.yaml"
        save_rubric(rubric, str(rubric_path))

        # Create submissions file
        submissions = [
            Submission(student_id="s1", answers={"Q1": "A"}),
            Submission(student_id="s2", answers={"Q1": "B"}),
        ]
        csv_path = tmp_path / "submissions.csv"
        save_submissions_to_csv(submissions, str(csv_path))

        # Grade from files
        result = grade_from_files(str(rubric_path), str(csv_path))
        assert len(result.results) == 2
        assert result.results[0].total_points == 10
        assert result.results[1].total_points == 0

    def test_grade_from_files_custom_student_col(self, tmp_path):
        """Test grading from files with custom student ID column."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(
                    question_id="Q1", correct_answer="A", max_points=10, description="Test"
                )
            ],
        )
        rubric_path = tmp_path / "rubric.yaml"
        save_rubric(rubric, str(rubric_path))

        # Create CSV with custom column name
        csv_path = tmp_path / "submissions.csv"
        csv_path.write_text("StudentID,Q1\ns1,A\ns2,B\n")

        result = grade_from_files(str(rubric_path), str(csv_path), student_id_col="StudentID")
        assert len(result.results) == 2

    def test_grade_from_files_missing_rubric(self, tmp_path):
        """Test grading from files with missing rubric."""
        csv_path = tmp_path / "submissions.csv"
        csv_path.write_text("student_id,Q1\ns1,A\n")

        with pytest.raises(FileNotFoundError):
            grade_from_files("nonexistent.yaml", str(csv_path))

    def test_grade_from_files_missing_submissions(self, tmp_path):
        """Test grading from files with missing submissions."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(
                    question_id="Q1", correct_answer="A", max_points=10, description="Test"
                )
            ],
        )
        rubric_path = tmp_path / "rubric.yaml"
        save_rubric(rubric, str(rubric_path))

        with pytest.raises(FileNotFoundError):
            grade_from_files(str(rubric_path), "nonexistent.csv")

    def test_grade_from_files_with_metadata(self, tmp_path):
        """Test grading from files preserves metadata."""
        # Create rubric with metadata
        rubric = Rubric(
            name="Quiz",
            rules=[
                ExactMatchRule(
                    question_id="q1", correct_answer="A", max_points=10.0, description="Test"
                )
            ],
            metadata={"course": "CS101", "term": "Fall 2025"},
        )

        rubric_path = tmp_path / "rubric.yaml"
        save_rubric(rubric, str(rubric_path))

        # Create submissions CSV
        csv_path = tmp_path / "subs.csv"
        csv_path.write_text("student_id,q1\ns1,A\ns2,B\n")

        result = grade_from_files(str(rubric_path), str(csv_path))

        # Metadata is included in the result
        assert result.metadata["rubric_name"] == "Quiz"
        assert len(result.results) == 2


class TestErrorHandling:
    """Test error handling in core module."""

    def test_invalid_rule_type_in_rubric(self):
        """Test handling of invalid rule type."""
        # This should be caught by Pydantic validation
        with pytest.raises(ValidationError):
            Rubric(name="Test", rules=[{"type": "INVALID_TYPE", "question_id": "Q1"}])

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        with pytest.raises(ValidationError):
            ExactMatchRule(
                question_id="Q1",
                # Missing correct_answer and max_points
            )

    def test_invalid_points_value(self):
        """Test handling of invalid points value."""
        with pytest.raises(ValidationError):
            ExactMatchRule(
                question_id="Q1",
                correct_answer="A",
                max_points=-5.0,  # Negative points
            )

    def test_progress_callback_exception(self):
        """Test that exceptions in progress callback are handled gracefully."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(
                    question_id="q1", correct_answer="A", max_points=10.0, description="Test"
                )
            ],
        )

        submissions = [
            Submission(student_id="s1", answers={"q1": "A"}),
            Submission(student_id="s2", answers={"q1": "B"}),
        ]

        def failing_callback(current, total):
            raise RuntimeError("Callback failed!")

        # Should complete successfully despite callback failure
        result = grade(rubric, submissions, progress_callback=failing_callback)

        assert len(result.results) == 2
        assert result.results[0].total_points == 10.0

    def test_rule_processing_with_missing_answer(self):
        """Test handling when student doesn't provide an answer."""
        rubric = Rubric(
            name="Test",
            rules=[
                NumericRangeRule(
                    question_id="q1",
                    min_value=9.0,
                    max_value=11.0,
                    max_points=10.0,
                    description="Test",
                    unit="cm",
                )
            ],
        )

        # Missing answer should result in 0 points
        submission = Submission(student_id="s1", answers={})
        result = grade(rubric, [submission])

        assert result.results[0].total_points == 0.0
        assert len(result.results[0].grade_details) == 1

    def test_empty_submissions_list(self):
        """Test grading with empty submissions list."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(
                    question_id="q1", correct_answer="A", max_points=10.0, description="Test"
                )
            ],
        )

        result = grade(rubric, [])

        assert len(result.results) == 0
        assert result.metadata["total_submissions"] == 0

    def test_empty_answer_string(self):
        """Test grading with empty answer string."""
        rubric = Rubric(
            name="Test",
            rules=[
                LengthRule(
                    question_id="q1", min_words=5, max_words=10, max_points=10.0, description="Test"
                )
            ],
        )

        result = grade(rubric, [Submission(student_id="s1", answers={"q1": ""})])
        assert result.results[0].total_points == 0.0

    def test_rubric_with_no_rules(self):
        """Test grading with rubric that has no rules."""
        rubric = Rubric(name="Test", rules=[])
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])

        assert result.results[0].total_points == 0.0
        assert result.results[0].max_points == 0.0
        assert len(result.results[0].grade_details) == 0


class TestProgressCallback:
    """Test progress callback functionality in the grade function."""

    def test_progress_callback_called(self):
        """Test that progress callback is invoked during grading."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(
                    question_id="q1", correct_answer="test", max_points=10.0, description="Test"
                )
            ],
        )

        submissions = [Submission(student_id=f"s{i}", answers={"q1": "test"}) for i in range(5)]

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        result = grade(rubric, submissions, progress_callback=progress_callback)

        assert len(result.results) == 5
        assert len(progress_calls) == 5
        assert progress_calls[-1] == (5, 5)

    def test_progress_callback_with_mixed_results(self):
        """Test that progress callback continues even with invalid answers."""
        rubric = Rubric(
            name="Test",
            rules=[
                NumericRangeRule(
                    question_id="q1",
                    min_value=9.0,
                    max_value=11.0,
                    max_points=10.0,
                    description="Test",
                    unit="units",
                )
            ],
        )

        # Mix of valid and invalid numeric answers
        submissions = [
            Submission(student_id="s1", answers={"q1": "10"}),
            Submission(student_id="s2", answers={"q1": "not_a_number"}),
            Submission(student_id="s3", answers={"q1": "11"}),
        ]

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        result = grade(rubric, submissions, progress_callback=progress_callback)

        assert len(result.results) == 3
        assert len(progress_calls) == 3
