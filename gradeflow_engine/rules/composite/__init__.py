"""Composite grading rule."""

from ..registry import rule_registry
from .model import CompositeRule
from .processor import process_composite

rule_registry.register(
    rule_type="COMPOSITE",
    processor=process_composite,
    model=CompositeRule,
)

__all__ = [
    "CompositeRule",
    "process_composite",
]
