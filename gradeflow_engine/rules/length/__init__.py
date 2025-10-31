"""Length grading rule."""

from ..registry import rule_registry
from .model import LengthRule
from .processor import process_length

rule_registry.register(
    rule_type="LENGTH",
    processor=process_length,
    model=LengthRule,
)

__all__ = [
    "LengthRule",
    "process_length",
]
