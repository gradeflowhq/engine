"""Keyword grading rule."""

from ..registry import rule_registry
from .model import KeywordRule
from .processor import process_keyword

rule_registry.register(
    rule_type="KEYWORD",
    processor=process_keyword,
    model=KeywordRule,
)

__all__ = [
    "KeywordRule",
    "process_keyword",
]
