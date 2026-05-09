from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, create_model
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from ...exceptions import MissingAnswerError
from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..constraints import QuestionConstraint
from ..result import QuestionResult, Result
from ..types import RuleId, RuleValidationError
from ..validators import is_empty, validate_answer_type

if TYPE_CHECKING:
    from ..context import RuleContext, RulePath

DEFAULT_MAX_POINTS = 1.0
CONTEXT_OMIT_FIELDS = {"id", "scope", "display_name", "question_types", "constraints"}
INITIAL_OMIT_FIELDS = {"id", "display_name", "question_types", "constraints"}


def new_rule_id() -> RuleId:
    return uuid4().hex


def rule_type_field(default: str) -> Any:
    return Field(default=default, frozen=True, json_schema_extra={"readOnly": True})


def rule_display_name_field(default: str) -> Any:
    return Field(default=default, frozen=True, json_schema_extra={"readOnly": True})


def rule_question_types_field(question_types: Iterable[QuestionType]) -> Any:
    return Field(
        default=frozenset(question_types),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )


def rule_constraints_field(constraints: Iterable[QuestionConstraint]) -> Any:
    return Field(
        default=list(constraints),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )


def rule_scope_field(default: str) -> Any:
    return Field(default=default, frozen=True, json_schema_extra={"readOnly": True})


class BaseRule(BaseModel, ABC):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: RuleId = Field(default_factory=new_rule_id, json_schema_extra={"readOnly": True})
    question_types: frozenset[QuestionType] = rule_question_types_field(())
    constraints: list[QuestionConstraint] = rule_constraints_field(())

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        if "display_name" not in cls.model_fields:
            return

        cls.model_config = ConfigDict(
            **{
                **cls.model_config,
                "title": cast(str, cls.model_fields["display_name"].default),
            }
        )

    @classmethod
    def from_context(
        cls,
        context: "RuleContext",
    ) -> type[BaseModel]:
        fields: dict[str, tuple[object, FieldInfo]] = {
            field_name: (field_info.annotation, field_info)
            for field_name, field_info in cls.model_fields.items()
            if field_name not in CONTEXT_OMIT_FIELDS
        }
        fields.update(cls.field_overrides(context))
        return cast(
            type[BaseModel],
            create_model(cls.__name__, __config__=cls.model_config, **cast(Any, fields)),
        )

    @classmethod
    def field_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, tuple[object, FieldInfo]]:
        return {}

    @classmethod
    def initial_value_from_context(cls, context: "RuleContext") -> dict[str, Any]:
        initial: dict[str, Any] = {}
        for field_name, field_info in cls.model_fields.items():
            if field_name in INITIAL_OMIT_FIELDS:
                continue
            if field_info.default is not PydanticUndefined:
                initial[field_name] = field_info.default
            elif field_info.default_factory is not None:
                initial[field_name] = field_info.get_default(call_default_factory=True)

        if context.scope == "question" and context.question_id and context.slot_index is None:
            initial["question_id"] = context.question_id

        initial.update(cls.initial_value_overrides(context))
        return initial

    @classmethod
    def initial_value_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, Any]:
        return {}

    @classmethod
    def nested_context(
        cls,
        context: "RuleContext",
        path: "RulePath",
    ) -> "RuleContext | None":
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError("Subclasses must implement this method.")

    def validate_question_compatibility(self, question: Question) -> list[RuleValidationError]:
        rule_type = getattr(self, "type", self.__class__.__name__)
        errors: list[RuleValidationError] = []
        if question.type not in self.question_types:
            errors.append(
                f"Rule of type {rule_type} is not compatible with question type {question.type}."
            )
        return errors

    @abstractmethod
    def _process_answer(self, answer: Answer) -> Result:
        raise NotImplementedError("Subclasses must implement this method.")

    def process_answer(self, answer: Answer) -> Result:
        if is_empty(answer):
            return Result(
                output=0,
                passed=False,
                feedback="No answer provided.",
                rule="No Answer",
            )
        validate_answer_type(answer, self.question_types)
        return self._process_answer(answer)


class BaseQuestionRule(ABC):
    @abstractmethod
    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_target_question_ids(self) -> set[QuestionId]:
        raise NotImplementedError("Subclasses must implement this method.")

    def get_referenced_question_ids(self) -> set[QuestionId]:
        return self.get_target_question_ids()


class BaseSingleQuestionRule(BaseRule, BaseQuestionRule):
    scope: Literal["question"] = rule_scope_field("question")
    question_id: QuestionId

    @classmethod
    def field_overrides(
        cls,
        context: "RuleContext",
    ) -> dict[str, tuple[object, FieldInfo]]:
        question_types = cls.model_fields["question_types"].default
        if context.question_id and not context.question_id_editable:
            return {
                "question_id": (
                    Literal.__getitem__(context.question_id),
                    cast(
                        FieldInfo,
                        Field(
                            default=context.question_id,
                            frozen=True,
                            json_schema_extra={"readOnly": True},
                        ),
                    ),
                )
            }
        question_ids = [
            question_id
            for question_id, question in context.question_set.question_map.items()
            if question.type in question_types
        ]
        field_kwargs: dict[str, Any] = {}
        if question_ids:
            field_kwargs["json_schema_extra"] = {"enum": question_ids}
        return {
            "question_id": (
                str,
                cast(FieldInfo, Field(..., **field_kwargs)),
            )
        }

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        if self.question_id not in question_map:
            return []  # Question existence is validated elsewhere
        return self.validate_question_compatibility(question_map[self.question_id])

    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        if self.question_id not in question_ids:
            return [f"Question ID {self.question_id} does not exist in the assessment."]
        return []

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        return []

    def get_target_question_ids(self) -> set[QuestionId]:
        return {self.question_id}

    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points if result.passed else 0.0

    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        if self.question_id not in answer_map:
            raise MissingAnswerError(self.question_id)
        answer = answer_map[self.question_id]
        result = self.process_answer(answer)
        max_points = max_points_map.get(self.question_id, DEFAULT_MAX_POINTS)
        question_result = QuestionResult(
            **result.model_dump(),
            max_points=max_points,
            points=self.compute_points(result, max_points),
        )
        return {self.question_id: question_result}


class BaseMultiQuestionRule(BaseRule, BaseQuestionRule):
    scope: Literal["global"] = rule_scope_field("global")

    def _process_answer(self, answer: Answer) -> Result:
        raise NotImplementedError("Multi-question rules must process full submissions.")

    @abstractmethod
    def process_submission(
        self, answer_map: dict[QuestionId, Answer], max_points_map: dict[QuestionId, float]
    ) -> dict[QuestionId, QuestionResult]:
        raise NotImplementedError("Subclasses must implement this method.")
