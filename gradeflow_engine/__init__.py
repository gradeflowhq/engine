"""
Advanced Grader Engine - A powerful grading engine for digital assessments.

This package provides models and functionality for post-processing and re-grading
digital exam data with support for conditional dependencies, assumption-based grading,
and programmable grading rules.
"""

import logging

from .core import (
    grade,
    grade_from_files,
)
from .io import (
    export_results,
    load_rubric,
    load_schema,
    load_submissions_csv,
    save_results_csv,
    save_results_yaml,
    save_rubric,
    save_schema,
)
from .models import (
    AssumptionSetRule,
    BasicSingleQuestionRule,
    ComposableRule,
    CompositeRule,
    ConditionalRule,
    ExactMatchRule,
    GradeDetail,
    GradeOutput,
    GradingRule,
    KeywordRule,
    LengthRule,
    MultipleChoiceRule,
    MultipleQuestionRule,
    NumericRangeRule,
    ProgrammableRule,
    RegexRule,
    Rubric,
    SimilarityRule,
    SingleQuestionRule,
    StudentResult,
    Submission,
)
from .protocols import SchemaValidatable
from .schema import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    QuestionSchema,
    SchemaValidationError,
    TextQuestionSchema,
    infer_mcq_options,
    infer_schema_from_submissions,
    validate_rubric_against_schema,
    validate_rubric_against_schema_strict,
)
from .types import ExportFormat, QuestionType

__version__ = "0.1.0"


def configure_logging(
    level: str = "INFO",
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    date_format: str = "%Y-%m-%d %H:%M:%S",
) -> None:
    """
    Configure logging for the gradeflow engine.

    Sets up console logging with the specified level and format.
    Call this function early in your application if you want to see
    debug output or customize logging behavior.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log message format string
        date_format: Date/time format for log messages

    Example:
        >>> from gradeflow_engine import configure_logging
        >>> configure_logging(level="DEBUG")
        >>> # Now all debug messages will be visible
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    logging.basicConfig(
        level=numeric_level,
        format=format,
        datefmt=date_format,
        force=True,  # Override any existing configuration
    )


__all__ = [
    # Core functions
    "grade",
    "grade_from_files",
    # I/O functions
    "load_rubric",
    "save_rubric",
    "load_schema",
    "save_schema",
    "load_submissions_csv",
    "save_results_yaml",
    "save_results_csv",
    "export_results",
    # Models
    "Rubric",
    "Submission",
    "GradeDetail",
    "StudentResult",
    "GradeOutput",
    # Rule type unions
    "GradingRule",
    "SingleQuestionRule",
    "MultipleQuestionRule",
    "BasicSingleQuestionRule",
    "ComposableRule",
    # Single-question rule models
    "ExactMatchRule",
    "NumericRangeRule",
    "MultipleChoiceRule",
    "LengthRule",
    "SimilarityRule",
    "ProgrammableRule",
    "KeywordRule",
    "RegexRule",
    "CompositeRule",
    # Multiple-question rule models
    "ConditionalRule",
    "AssumptionSetRule",
    # Schema models and functions
    "AssessmentSchema",
    "QuestionSchema",
    "QuestionType",
    "ExportFormat",
    "ChoiceQuestionSchema",
    "NumericQuestionSchema",
    "TextQuestionSchema",
    "SchemaValidationError",
    "infer_schema_from_submissions",
    "infer_mcq_options",
    "validate_rubric_against_schema",
    "validate_rubric_against_schema_strict",
    # Protocols
    "SchemaValidatable",
    # Utilities
    "configure_logging",
    "__version__",
]
