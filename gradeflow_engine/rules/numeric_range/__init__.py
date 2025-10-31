"""Numeric range grading rule."""

from ..registry import rule_registry
from .model import NumericRangeRule
from .processor import process_numeric_range

rule_registry.register(
    rule_type="NUMERIC_RANGE",
    processor=process_numeric_range,
    model=NumericRangeRule,
)

__all__ = [
    "NumericRangeRule",
    "process_numeric_range",
]
