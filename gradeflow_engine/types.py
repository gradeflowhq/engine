"""
Common type definitions for gradeflow engine.

This module contains type aliases that are used across the engine
to avoid circular imports.
"""

from typing import Literal

# Type alias for question types
QuestionType = Literal["CHOICE", "NUMERIC", "TEXT"]
