from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal, TypeAlias, cast

from ..question_sets.model import QuestionSet
from ..questions.models import Question
from ..questions.models.multi_valued import MultiValuedQuestion
from ..questions.types import QuestionId, QuestionType
from ..submissions.models import Submission

RuleScope: TypeAlias = Literal["global", "question", "value"]
RulePath: TypeAlias = tuple[str | int, ...]


@dataclass(frozen=True)
class RuleContext:
    scope: RuleScope
    question_set: QuestionSet
    submissions: Sequence[Submission] = ()
    question_id: QuestionId | None = None
    question: Question | None = None
    question_id_editable: bool = False
    slot_index: int | None = None

    @property
    def question_type(self) -> QuestionType | None:
        if isinstance(self.question, MultiValuedQuestion) and self.slot_index is not None:
            return cast(QuestionType, self.question.value_types[self.slot_index])
        return self.question.type if self.question else None

    def for_question_rules(self) -> RuleContext:
        return replace(self, scope="question", question_id_editable=True, slot_index=None)

    def for_value_rules(self) -> RuleContext:
        if self.question is None:
            raise ValueError("Value rule context requires a question")
        return replace(self, scope="value")

    def for_value_slot(self, index: int) -> RuleContext:
        if not isinstance(self.question, MultiValuedQuestion):
            raise ValueError("Value slot context requires a multi-valued question")
        if index < 0 or index >= len(self.question.value_types):
            raise ValueError(
                f"Value slot {index} does not exist for question with "
                f"{len(self.question.value_types)} values"
            )
        return replace(self, scope="value", slot_index=index)

    def answer_suggestions(self) -> list[str]:
        if not self.question_id or not self.question:
            return []

        suggestions: list[str] = []
        for submission in self.submissions:
            answer = submission.answer_map.get(self.question_id)
            if answer is None:
                continue
            suggestion = self._answer_suggestion(answer)
            if suggestion and suggestion not in suggestions:
                suggestions.append(suggestion)
        return suggestions

    def _answer_suggestion(self, answer: object) -> str | None:
        if isinstance(self.question, MultiValuedQuestion) and self.slot_index is not None:
            if not isinstance(answer, list) or self.slot_index >= len(answer):
                return None
            answer = answer[self.slot_index]
        return None if answer is None else str(answer)
