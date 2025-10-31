"""Regex grading rule."""

from ..registry import rule_registry
from .model import RegexRule
from .processor import process_regex

rule_registry.register(
    rule_type="REGEX",
    processor=process_regex,
    model=RegexRule,
)

__all__ = [
    "RegexRule",
    "process_regex",
]
