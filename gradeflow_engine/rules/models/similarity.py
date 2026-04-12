from __future__ import annotations

import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from pydantic import Field, computed_field
from rapidfuzz.distance import JaroWinkler, Levenshtein

from ...questions.types import Answer, QuestionType
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule

if TYPE_CHECKING:
    from fastembed import TextEmbedding


TRANSFORMER_MODEL = "BAAI/bge-small-en-v1.5"


def _raise_algorithm_import_error(algorithm: str) -> ImportError:
    return ImportError(
        f"The '{algorithm}' algorithm requires the 'ml' extra. Install it with: pip install '.[ml]'"
    )


@functools.cache
def _get_transformer_model() -> TextEmbedding:
    try:
        from fastembed import TextEmbedding
    except ImportError as e:
        raise _raise_algorithm_import_error("transformer") from e
    return TextEmbedding(TRANSFORMER_MODEL)


def _best_score(scores: list[float]) -> tuple[float, int]:
    best = max(range(len(scores)), key=lambda i: scores[i])
    return scores[best], best


def _rapidfuzz_similarity(
    fn: Callable[[str, str], float], answer: str, references: list[str]
) -> tuple[float, int]:
    return _best_score([fn(answer, ref) for ref in references])


def _levenshtein_similarity(answer: str, references: list[str]) -> tuple[float, int]:
    return _rapidfuzz_similarity(Levenshtein.normalized_similarity, answer, references)


def _jaro_winkler_similarity(answer: str, references: list[str]) -> tuple[float, int]:
    return _rapidfuzz_similarity(JaroWinkler.normalized_similarity, answer, references)


def _transformer_similarity(answer: str, references: list[str]) -> tuple[float, int]:
    try:
        import numpy as np
    except ImportError as e:
        raise _raise_algorithm_import_error("transformer") from e
    model = _get_transformer_model()
    ref_embeddings: list[np.ndarray] = list(model.passage_embed(references))
    query_embedding = list(model.query_embed([answer]))[0]
    scores: list[float] = np.clip(np.dot(ref_embeddings, query_embedding), 0, 1).tolist()
    return _best_score(scores)


AlgorithmFn = Callable[[str, list[str]], tuple[float, int]]

ALGORITHM_MAP: dict[str, AlgorithmFn] = {
    "levenshtein": _levenshtein_similarity,
    "jaro_winkler": _jaro_winkler_similarity,
    "transformer": _transformer_similarity,
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
    algorithm: Literal["levenshtein", "jaro_winkler", "transformer"] = Field(
        default="levenshtein",
        description=(
            "Similarity algorithm to use "
            "(options: 'levenshtein', 'jaro_winkler', 'transformer'). "
            f"'transformer' uses the {TRANSFORMER_MODEL} model and requires the 'ml' extra."
        ),
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
        closest_similarity, best_idx = similarity_fn(str(answer), self.references)
        closest_ref = self.references[best_idx]
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
