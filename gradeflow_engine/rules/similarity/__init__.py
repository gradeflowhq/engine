"""Similarity grading rule."""

from ..registry import rule_registry
from .model import SimilarityRule
from .processor import process_similarity

rule_registry.register(
    rule_type="SIMILARITY",
    processor=process_similarity,
    model=SimilarityRule,
)

__all__ = [
    "SimilarityRule",
    "process_similarity",
]
