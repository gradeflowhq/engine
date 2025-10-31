"""
Tests for rule utilities.

Run with: pytest tests/test_utils.py -v
"""

import pytest

from gradeflow_engine.rules.utils import (
    format_feedback,
    format_keyword_feedback,
    format_similarity_feedback,
    sanitize_text,
    validate_question_id,
)


class TestSanitizeText:
    """Test text sanitization."""

    def test_normal_text(self):
        """Test normal text passes through."""
        text = "This is normal text"
        assert sanitize_text(text) == text

    def test_empty_string(self):
        """Test empty string."""
        assert sanitize_text("") == ""

    def test_control_characters_removed(self):
        """Test control characters are removed."""
        text = "Text\x00with\x01control\x02chars"
        result = sanitize_text(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result
        assert "Textwithcontrolchars" == result

    def test_max_length_truncation(self):
        """Test text is truncated at max_length."""
        text = "a" * 1000
        result = sanitize_text(text, max_length=100)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_max_length_no_truncation(self):
        """Test text under max_length is not truncated."""
        text = "Short text"
        result = sanitize_text(text, max_length=100)
        assert result == text
        assert not result.endswith("...")

    def test_unicode_preserved(self):
        """Test Unicode characters are preserved."""
        text = "Hello 世界 🌍"
        result = sanitize_text(text)
        assert "世界" in result
        assert "🌍" in result

    def test_newlines_preserved(self):
        """Test newlines are preserved."""
        text = "Line1\nLine2"
        result = sanitize_text(text)
        assert "\n" in result

    def test_tabs_preserved(self):
        """Test tabs are preserved."""
        text = "Tab\there"
        result = sanitize_text(text)
        assert "\t" in result or " " in result  # Either preserved or converted


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


class TestFormatSimilarityFeedback:
    """Test similarity feedback formatting."""

    def test_high_similarity(self):
        """Test high similarity feedback."""
        result = format_similarity_feedback(0.95, 0.8)
        assert "95" in result or "0.95" in result
        assert "threshold" in result.lower()

    def test_low_similarity(self):
        """Test low similarity feedback."""
        result = format_similarity_feedback(0.5, 0.8)
        assert "50" in result or "0.5" in result

    def test_exact_threshold(self):
        """Test similarity exactly at threshold."""
        result = format_similarity_feedback(0.8, 0.8)
        assert "80" in result or "0.8" in result


class TestFormatKeywordFeedback:
    """Test keyword feedback formatting."""

    def test_all_required_found(self):
        """Test feedback when all required keywords found."""
        result = format_keyword_feedback(
            found_required=["python", "java"], missing_required=[], found_optional=["ruby"]
        )
        assert "required" in result.lower()

    def test_missing_required(self):
        """Test feedback when required keywords missing."""
        result = format_keyword_feedback(
            found_required=["python"], missing_required=["java", "c++"], found_optional=[]
        )
        assert "missing" in result.lower()

    def test_optional_found(self):
        """Test feedback with optional keywords."""
        result = format_keyword_feedback(
            found_required=["python"], missing_required=[], found_optional=["ruby", "go"]
        )
        assert "bonus" in result.lower()

    def test_no_keywords(self):
        """Test feedback with no keywords."""
        result = format_keyword_feedback(found_required=[], missing_required=[], found_optional=[])
        assert isinstance(result, str)
        assert "no keywords" in result.lower()
