from collections.abc import Callable
from typing import Literal

from pydantic import Field
from rapidfuzz.distance import JaroWinkler, Levenshtein

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule

ALGORITHM_MAP: dict[str, Callable[..., float]] = {
    "levenshtein": Levenshtein.normalized_similarity,
    "jaro_winkler": JaroWinkler.normalized_similarity,
}


class SimilarityRule(BaseRule):
    """A rule that checks for similarity between the student's answer and a reference text."""

    question_types: frozenset[QuestionType] = frozenset({"TEXT"})
    reference: str = Field(..., description="Reference text for similarity comparison")
    threshold: float = Field(
        default=0.8, description="Similarity threshold for passing the rule (0 to 1)"
    )
    algorithm: Literal["levenshtein", "jaro_winkler"] = Field(
        default="levenshtein",
        description="Similarity algorithm to use (options: 'levenshtein', 'jaro_winkler')",
    )

    def _process_answer(self, answer: Answer) -> Result:
        similarity_fn = ALGORITHM_MAP[self.algorithm]
        similarity = similarity_fn(str(answer), self.reference)
        passed = similarity >= self.threshold
        feedback = (
            f"✓ Match: {similarity:.0%} (threshold: {self.threshold:.0%})"
            if passed
            else f"✗ Insufficient similarity: {similarity:.0%} < {self.threshold:.0%}"
        )
        return Result(
            output=similarity,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class SimilarityQuestionRule(SimilarityRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points if result.passed else 0.0
