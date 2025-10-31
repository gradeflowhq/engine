"""
Shared utilities for rule processors.

Provides common functions for sanitization, validation, and feedback formatting.
"""


def sanitize_text(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input for safe display in feedback and logging.

    Removes control characters, limits length, and prevents injection attacks.

    Args:
        text: Text to sanitize
        max_length: Maximum length to truncate to

    Returns:
        Sanitized text safe for display
    """
    if not text:
        return ""

    # Truncate to max length
    text = text[:max_length]

    # Remove control characters but keep common whitespace
    text = "".join(c for c in text if c.isprintable() or c in ("\n", "\t", " "))

    # If truncated, add ellipsis
    if len(text) >= max_length:
        text = text[: max_length - 3] + "..."

    return text


def validate_question_id(question_id: str) -> str:
    """
    Validate and normalize question ID.

    Args:
        question_id: Question ID to validate

    Returns:
        Normalized question ID

    Raises:
        ValueError: If question ID is invalid
    """
    if not question_id or not question_id.strip():
        raise ValueError("question_id cannot be empty or whitespace")

    question_id = question_id.strip()

    # Optionally enforce format (commented out - may be too strict)
    # if not re.match(r'^[a-zA-Z0-9_-]+$', question_id):
    #     raise ValueError(
    #         f"question_id '{question_id}' must be alphanumeric with _ or - only"
    #     )

    return question_id


def format_feedback(
    is_correct: bool, expected: str | None = None, details: str | None = None
) -> str:
    """
    Format consistent feedback messages.

    Args:
        is_correct: Whether the answer is correct
        expected: Expected answer (if applicable)
        details: Additional details

    Returns:
        Formatted feedback string
    """
    if is_correct:
        prefix = "✓ Correct"
        if details:
            return f"{prefix}: {details}"
        return prefix
    else:
        prefix = "✗ Incorrect"
        parts = [prefix]
        if expected:
            parts.append(f"Expected: {sanitize_text(expected, max_length=100)}")
        if details:
            parts.append(details)
        return " - ".join(parts)


def format_similarity_feedback(similarity: float, threshold: float) -> str:
    """
    Format feedback for similarity-based grading.

    Args:
        similarity: Similarity score (0-1)
        threshold: Threshold for passing

    Returns:
        Formatted feedback string
    """
    if similarity >= threshold:
        return f"✓ Match: {similarity:.0%} (threshold: {threshold:.0%})"
    return f"✗ Insufficient similarity: {similarity:.0%} < {threshold:.0%}"


def format_keyword_feedback(
    found_required: list, missing_required: list, found_optional: list
) -> str:
    """
    Format feedback for keyword-based grading.

    Args:
        found_required: List of required keywords found
        missing_required: List of required keywords missing
        found_optional: List of optional keywords found

    Returns:
        Formatted feedback string
    """
    parts = []

    if missing_required:
        parts.append(f"✗ Missing required: {', '.join(missing_required)}")
    elif found_required:
        parts.append("✓ Found all required keywords")

    if found_optional:
        parts.append(f"+ Bonus: {', '.join(found_optional)}")

    return "; ".join(parts) if parts else "No keywords found"
