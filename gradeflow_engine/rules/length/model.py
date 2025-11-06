"""Length rule model definition."""

from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import Field, field_validator

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class LengthRule(BaseSingleQuestionRule):
    """Grade an answer based on length constraints."""

    type: Literal["LENGTH"] = "LENGTH"
    compatible_types: ClassVar[frozenset[QuestionType]] = frozenset({"TEXT"})

    min_length: int | None = Field(
        default=None, ge=0, description="Minimum length (chars or words)"
    )
    max_length: int | None = Field(
        default=None, ge=0, description="Maximum length (chars or words)"
    )
    mode: Literal["characters", "words"] = Field(
        default="characters",
        description="Measure by 'characters' or 'words' (whitespace-separated tokens)",
    )

    @field_validator("max_length")
    @classmethod
    def validate_max_ge_min(cls, v: int | None, info: Any) -> int | None:
        min_v = info.data.get("min_length")
        if v is not None and min_v is not None and v < min_v:
            raise ValueError("max_length must be greater than or equal to min_length")
        return v

    @field_validator("min_length", "max_length")
    @classmethod
    def ensure_at_least_one_constraint(cls, v: int | None, info: Any) -> int | None:
        # Ensure at least one constraint is set across the two fields
        data = info.data
        if data.get("min_length") is None and data.get("max_length") is None and v is None:
            raise ValueError("At least one of min_length or max_length must be specified")
        return v

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        from gradeflow_engine.rules.utils import validate_type_compatibility

        return validate_type_compatibility(
            schema=schema,
            compatible_types=self.compatible_types,
            rule_description=rule_description,
            rule_name="LengthRule",
        )
