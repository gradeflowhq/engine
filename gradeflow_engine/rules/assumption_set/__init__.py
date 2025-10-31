"""Assumption set grading rule."""

from ..registry import rule_registry
from .model import AssumptionSetRule
from .processor import process_assumption_set

rule_registry.register(
    rule_type="ASSUMPTION_SET",
    processor=process_assumption_set,
    model=AssumptionSetRule,
)

__all__ = [
    "AssumptionSetRule",
    "process_assumption_set",
]
