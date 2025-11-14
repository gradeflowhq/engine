"""
Programmable grading rule that runs a small user-provided Python fragment
to evaluate an answer and produce points and optional feedback.
"""

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class ProgrammableRule(BaseSingleQuestionRule):
    """Write a code to set points_awarded and optional feedback for a target question."""

    type: Literal["PROGRAMMABLE"] = "PROGRAMMABLE"

    # Programmable rules are compatible with all core question types
    compatible_types: frozenset[QuestionType] = frozenset({"CHOICE", "NUMERIC", "TEXT"})

    code: str = Field(
        ...,
        description=(
            "Python code fragment to evaluate the student's answer. The code "
            "will run in a sandboxed environment with access to `student_answers`, "
            "`question_id`, `answer`, and `rule`. It MUST set `points_awarded` (float) "
            "and may optionally set `feedback` (str)."
        ),
    )

    def validate_against_question_schema(
        self, question_map: dict[str, "QuestionSchema"], rule_description: str
    ) -> list[str]:
        return []  # It can run on any question type
