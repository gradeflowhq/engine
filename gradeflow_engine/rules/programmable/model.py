"""Programmable rule model definition."""

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from gradeflow_engine.types import QuestionType

from ..base import BaseSingleQuestionRule

if TYPE_CHECKING:
    from gradeflow_engine.schema import QuestionSchema


class ProgrammableRule(BaseSingleQuestionRule):
    """
    Programmable grading rule - user-provided code is stored in `code`.

    The `code` string should contain a small Python fragment that evaluates
    the student's answer for the target `question_id` and sets the following
    variables as its outputs (the processor will read these after execution):

    Required outputs (must be set by the code):
      - points_awarded: float
          Number of max_points to award for this question (can be 0.0).

    Optional outputs (may be set by the code):
      - feedback: str
          Human readable feedback for the student.

    Available inputs / helper variables provided to the execution environment:
      - student_answers: dict[str, str]
          All answers from the student's submission (question_id -> answer string).
      - question_id: str
          The question id this rule targets.
      - answer: str
          The student's answer for the current question (equivalent to
          student_answers[question_id]).
    """

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

    def validate_against_schema(
        self, question_id: str, schema: "QuestionSchema", rule_description: str
    ) -> list[str]:
        # ProgrammableRule can work with any question type; no type-specific validation
        return []
