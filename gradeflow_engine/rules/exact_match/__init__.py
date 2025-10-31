"""Exact match grading rule."""

from ..registry import rule_registry
from .model import ExactMatchRule
from .processor import process_exact_match

# Register the rule
rule_registry.register(
    rule_type="EXACT_MATCH",
    processor=process_exact_match,
    model=ExactMatchRule,
)

__all__ = [
    "ExactMatchRule",
    "process_exact_match",
]
