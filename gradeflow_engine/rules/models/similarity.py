from collections.abc import Callable
from typing import Literal

from pydantic import Field, computed_field
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

    type: Literal["SIMILARITY"] = Field(
        default="SIMILARITY", frozen=True, json_schema_extra={"readOnly": True}
    )
    name: Literal["Similarity"] = Field(
        default="Similarity", frozen=True, json_schema_extra={"readOnly": True}
    )
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"TEXT"}), frozen=True, json_schema_extra={"readOnly": True}
    )
    references: list[str] = Field(..., description="Reference answers for similarity comparison")
    threshold: float = Field(
        default=0.8, description="Similarity threshold for passing the rule (0 to 1)"
    )
    algorithm: Literal["levenshtein", "jaro_winkler"] = Field(
        default="levenshtein",
        description="Similarity algorithm to use (options: 'levenshtein', 'jaro_winkler')",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return (
            f"Similarity to one of the reference answers "
            f"{', '.join([f'`{ref}`' for ref in self.references])} "
            f"is at least {self.threshold:.0%} "
            f"using {self.algorithm.replace('_', ' ').title()} similarity."
        )

    def _process_answer(self, answer: Answer) -> Result:
        similarity_fn = ALGORITHM_MAP[self.algorithm]
        results = [(similarity_fn(str(answer), ref), ref) for ref in self.references]
        closest_similarity, closest_ref = max(results, key=lambda x: x[0])
        passed = closest_similarity >= self.threshold
        feedback = (
            (
                f'✓ Match: {closest_similarity:.0%} to reference "{closest_ref}" '
                f"(threshold: {self.threshold:.0%})"
            )
            if passed
            else (
                f"✗ Insufficient similarity: {closest_similarity:.0%} "
                f'to reference "{closest_ref}" < threshold {self.threshold:.0%}'
            )
        )
        return Result(
            output=closest_similarity,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class SimilarityQuestionRule(SimilarityRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points if result.passed else 0.0
