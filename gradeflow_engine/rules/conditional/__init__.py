"""Conditional grading rule."""

from ..registry import rule_registry
from .model import ConditionalRule
from .processor import process_conditional

rule_registry.register(
    rule_type="CONDITIONAL",
    processor=process_conditional,
    model=ConditionalRule,
)

__all__ = [
    "ConditionalRule",
    "process_conditional",
]
