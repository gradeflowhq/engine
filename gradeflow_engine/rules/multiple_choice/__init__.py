"""Multiple choice grading rule."""

from ..registry import rule_registry
from .model import MultipleChoiceRule
from .processor import process_multiple_choice

rule_registry.register(
    rule_type="MULTIPLE_CHOICE",
    processor=process_multiple_choice,
    model=MultipleChoiceRule,
)

__all__ = [
    "MultipleChoiceRule",
    "process_multiple_choice",
]
