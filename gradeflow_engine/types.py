"""
Common type definitions for gradeflow engine.

This module contains type aliases that are used across the engine
to avoid circular imports.
"""

from typing import Literal

# Type alias for question types
QuestionType = Literal["CHOICE", "NUMERIC", "TEXT"]

# Type alias for export formats
# These are the supported output formats for grading results
ExportFormat = Literal["yaml", "csv_summary", "csv_detailed", "canvas"]
