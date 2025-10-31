"""
Core public API for the gradeflow engine.

This module exposes the pure engine entrypoints and convenient I/O wrappers.
Includes the main grading logic and public API functions.
"""

import logging
from collections.abc import Callable

from pydantic import ValidationError

from .io import (
    load_rubric,
    load_submissions_csv,
)
from .models import (
    GradeDetail,
    GradeOutput,
    Rubric,
    StudentResult,
    Submission,
)
from .rules.registry import rule_registry
from .sandbox import SandboxExecutionError, SandboxTimeoutError

logger = logging.getLogger(__name__)


def grade(
    rubric: Rubric,
    submissions: list[Submission],
    progress_callback: Callable[[int, int], None] | None = None,
) -> GradeOutput:
    """
    Grade submissions using a rubric.

    This is the main API function for grading. It takes a rubric and a list
    of submissions and returns detailed grading results.

    Args:
        rubric: The grading rubric containing all rules
        submissions: List of student submissions to grade
        progress_callback: Optional callback function(current, total) for progress updates

    Returns:
        GradeOutput containing results for all students

    Example:
        >>> from gradeflow_engine import grade, Rubric, Submission, ExactMatchRule
        >>>
        >>> rubric = Rubric(
        ...     name="Quiz 1",
        ...     rules=[
        ...         ExactMatchRule(
        ...             question_id="Q1",
        ...             correct_answer="Paris",
        ...             max_points=10.0
        ...         )
        ...     ]
        ... )
        >>>
        >>> submissions = [
        ...     Submission(student_id="alice", answers={"Q1": "Paris"}),
        ...     Submission(student_id="bob", answers={"Q1": "London"})
        ... ]
        >>>
        >>> results = grade(rubric, submissions)
        >>> print(results.results[0].percentage)  # Alice: 100.0
        >>> print(results.results[1].percentage)  # Bob: 0.0

        With progress callback:
        >>> def on_progress(current, total):
        ...     print(f"Grading {current}/{total}")
        >>> results = grade(rubric, submissions, progress_callback=on_progress)
    """
    logger.info(f"Grading {len(submissions)} submissions using rubric '{rubric.name}'")
    logger.debug(f"Rubric has {len(rubric.rules)} rules")

    results = []

    for i, submission in enumerate(submissions, start=1):
        logger.debug(f"Grading submission for student {submission.student_id}")
        student_result = _grade_single_submission(rubric, submission)
        results.append(student_result)
        logger.debug(
            f"Student {submission.student_id}: "
            f"{student_result.total_points}/{student_result.max_points} "
            f"({student_result.percentage:.2f}%)"
        )

        # Call progress callback if provided
        if progress_callback:
            try:
                progress_callback(i, len(submissions))
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    logger.info(f"Completed grading {len(results)} submissions")

    return GradeOutput(
        results=results,
        metadata={
            "rubric_name": rubric.name,
            "total_submissions": len(submissions),
        },
    )


def _grade_single_submission(rubric: Rubric, submission: Submission) -> StudentResult:
    """
    Grade a single submission against all rules in the rubric.

    Args:
        rubric: The grading rubric
        submission: The student's submission

    Returns:
        StudentResult with detailed grading information
    """
    all_details: list[GradeDetail] = []

    for rule in rubric.rules:
        try:
            logger.debug(f"Applying rule type={rule.type}")

            # Get the appropriate processor for this rule type
            processor = rule_registry.get_processor(rule.type)

            # Apply the rule - processors can return single GradeDetail, List, or None
            result = processor(rule, submission)

            # Handle different return types
            if result is None:
                logger.debug(f"Rule {rule.type} returned None (condition not met or skipped)")
                continue
            elif isinstance(result, list):
                logger.debug(f"Rule {rule.type} returned {len(result)} grade details")
                all_details.extend(result)
            else:
                logger.debug(f"Rule {rule.type} returned single grade detail")
                all_details.append(result)

        except ValidationError as e:
            # Pydantic validation error
            logger.error(f"Validation error in rule {rule.type}: {e}", exc_info=False)
            error_detail = GradeDetail(
                question_id=getattr(rule, "question_id", "unknown"),
                student_answer=None,
                correct_answer=None,
                points_awarded=0.0,
                max_points=getattr(rule, "max_points", 0.0),
                is_correct=False,
                rule_applied=rule.type,
                feedback=f"✗ Validation error: {str(e)[:100]}",
            )
            all_details.append(error_detail)
        except (SandboxExecutionError, SandboxTimeoutError) as e:
            # Sandbox-specific errors from programmable rules
            logger.error(f"Sandbox error in rule {rule.type}: {e}", exc_info=False)
            error_detail = GradeDetail(
                question_id=getattr(rule, "question_id", "unknown"),
                student_answer=None,
                correct_answer=None,
                points_awarded=0.0,
                max_points=getattr(rule, "max_points", 0.0),
                is_correct=False,
                rule_applied=rule.type,
                feedback=f"✗ Script error: {str(e)[:100]}",
            )
            all_details.append(error_detail)
        except ValueError as e:
            # Known error (e.g., unknown rule type, invalid data)
            logger.error(f"ValueError in rule {rule.type}: {e}", exc_info=False)
            error_detail = GradeDetail(
                question_id=getattr(rule, "question_id", "unknown"),
                student_answer=None,
                correct_answer=None,
                points_awarded=0.0,
                max_points=getattr(rule, "max_points", 0.0),
                is_correct=False,
                rule_applied=rule.type,
                feedback=f"✗ Error: {str(e)[:100]}",
            )
            all_details.append(error_detail)
        except (KeyboardInterrupt, SystemExit):
            # Don't catch these - let them propagate
            raise
        except Exception as e:
            # Unexpected error - log with full traceback
            logger.exception(f"Unexpected error processing rule {rule.type}: {e}")
            error_detail = GradeDetail(
                question_id=getattr(rule, "question_id", "unknown"),
                student_answer=None,
                correct_answer=None,
                points_awarded=0.0,
                max_points=getattr(rule, "max_points", 0.0),
                is_correct=False,
                rule_applied=rule.type,
                feedback=f"✗ Unexpected error: {type(e).__name__}",
            )
            all_details.append(error_detail)

    # Calculate total score
    total_points = sum(detail.points_awarded for detail in all_details)
    max_points = sum(detail.max_points for detail in all_details)
    percentage = (total_points / max_points * 100) if max_points > 0 else 0.0

    return StudentResult(
        student_id=submission.student_id,
        total_points=total_points,
        max_points=max_points,
        percentage=percentage,
        grade_details=all_details,
        metadata=submission.metadata,
    )


def grade_from_files(
    rubric_path: str, submissions_csv_path: str, student_id_col: str = "student_id"
) -> GradeOutput:
    """
    Grade submissions loaded from files.

    Convenience function that loads rubric from YAML and submissions from CSV,
    then grades them.

    Args:
        rubric_path: Path to YAML rubric file
        submissions_csv_path: Path to submissions CSV file
        student_id_col: Name of student ID column in CSV (default: "student_id")

    Returns:
        GradeOutput containing results for all students

    Raises:
        FileNotFoundError: If rubric or submissions file doesn't exist
        ValueError: If files are invalid
    """
    rubric = load_rubric(rubric_path)
    submissions = load_submissions_csv(submissions_csv_path, student_id_col=student_id_col)

    return grade(rubric, submissions)
