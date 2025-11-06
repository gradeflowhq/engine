"""
Tests for rule utilities.

Run with: pytest tests/test_utils.py -v
"""

import pytest

from gradeflow_engine.rules.utils import (
    format_feedback,
    validate_question_id,
)


class TestValidateQuestionId:
    """Test question ID validation."""

    def test_valid_question_id(self):
        """Test valid question IDs."""
        assert validate_question_id("Q1") == "Q1"
        assert validate_question_id("question_1") == "question_1"
        assert validate_question_id("Q-1") == "Q-1"

    def test_empty_question_id(self):
        """Test empty question ID raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_question_id("")

    def test_whitespace_only_question_id(self):
        """Test whitespace-only question ID raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_question_id("   ")

    def test_question_id_trimmed(self):
        """Test question ID is trimmed."""
        assert validate_question_id("  Q1  ") == "Q1"


class TestFormatFeedback:
    """Test feedback formatting."""

    def test_basic_correct_feedback(self):
        """Test basic correct feedback without details."""
        result = format_feedback(True)
        assert "Correct" in result

    def test_basic_incorrect_feedback(self):
        """Test basic incorrect feedback without details."""
        result = format_feedback(False)
        assert "Incorrect" in result

    def test_feedback_with_expected(self):
        """Test feedback with expected value."""
        result = format_feedback(False, expected="Paris")
        assert "Incorrect" in result
        assert "Paris" in result

    def test_feedback_with_details(self):
        """Test feedback with details."""
        result = format_feedback(False, details="Match found at position 5")
        assert "Incorrect" in result
        assert "Match found at position 5" in result

    def test_feedback_correct_with_details(self):
        """Test correct feedback with details."""
        result = format_feedback(True, details="Exact match")
        assert "Correct" in result
        assert "Exact match" in result
