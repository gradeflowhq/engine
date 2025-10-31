"""Programmable grading rule."""

from ..registry import rule_registry
from .model import ProgrammableRule
from .processor import process_programmable

rule_registry.register(
    rule_type="PROGRAMMABLE",
    processor=process_programmable,
    model=ProgrammableRule,
)

__all__ = [
    "ProgrammableRule",
    "process_programmable",
]
