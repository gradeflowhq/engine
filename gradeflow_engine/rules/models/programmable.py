from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field

from ...questions.types import Answer, QuestionType
from ..executors import python
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule

ProgrammableMode = Literal["PASS_FAIL", "OUTPUT"]


TIME_LIMIT_S = 5


DEFAULT_PROGRAMMABLE_CODE = """\
# 'answer' variable contains the student's answer (can be str, float, list, or set)
# You must set the following variables:
# 'output' (float): A number between 0 and 1; max_points multiplier (only used in OUTPUT mode)
# 'passed' (bool): Whether the answer passed (only used in PASS_FAIL mode)
# 'feedback' (str, optional): Feedback to provide to the student
"""


@dataclass(frozen=True)
class ProgrammableResult:
    output: float
    passed: bool
    feedback: str


def evaluate(code: str, answer: Answer) -> ProgrammableResult:
    variables: dict[str, Any] = {
        "answer": answer,
    }
    try:
        python.run(code, variables, time_limit_s=TIME_LIMIT_S)
    except Exception as e:
        return ProgrammableResult(
            output=0.0,
            passed=False,
            feedback=f"Error during code execution: {e}",
        )

    try:
        output = float(variables.get("output", 0.0))
        passed = bool(variables.get("passed", False))
        feedback = str(variables.get("feedback", "No feedback provided."))
    except Exception as e:
        return ProgrammableResult(
            output=0.0,
            passed=False,
            feedback=f"Error retrieving result variables: {e}",
        )

    return ProgrammableResult(
        output=output,
        passed=passed,
        feedback=feedback,
    )


class ProgrammableRule(BaseRule):
    type: Literal["PROGRAMMABLE"] = "PROGRAMMABLE"
    question_types: frozenset[QuestionType] = frozenset({"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"})
    code: str = Field(
        default=DEFAULT_PROGRAMMABLE_CODE,
        description="Code to evaluate the answer. "
        "Required variables: 'output', 'passed'. "
        "Optional variable: 'feedback'.",
    )
    mode: ProgrammableMode = Field(
        default="PASS_FAIL",
        description=(
            "Mode of evaluation: "
            "'PASS_FAIL' uses a boolean 'passed' variable, "
            "'OUTPUT' uses the 'output' variable (0-1) for scoring."
        ),
    )

    def _process_answer(self, answer: Answer) -> Result:
        result = evaluate(self.code, answer)
        return Result(
            output=result.output,
            passed=result.passed,
            feedback=result.feedback,
            rule=self.__class__.__name__,
        )


class ProgrammableQuestionRule(ProgrammableRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        if self.mode == "OUTPUT":
            return result.output * self.max_points
        elif self.mode == "PASS_FAIL":
            return self.max_points if result.passed else 0.0
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
