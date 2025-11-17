from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field

from ...questions.types import Answer, QuestionType
from ..executors.restricted_python import safe_exec
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule

ProgrammableMode = Literal["PASS_FAIL", "OUTPUT"]


@dataclass(frozen=True)
class ProgrammableResult:
    output: float
    passed: bool
    feedback: str


def evaluate(code: str, answer: Answer) -> ProgrammableResult:
    local_vars: dict[str, Any] = {
        "answer": answer,
    }
    try:
        safe_exec(code, local_vars)
    except Exception as e:
        return ProgrammableResult(
            output=0.0,
            passed=False,
            feedback=f"Error during code execution: {e}",
        )

    output = local_vars.get("output", 0.0)
    passed = local_vars.get("passed", False)
    feedback = local_vars.get("feedback", "No feedback provided.")

    return ProgrammableResult(
        output=output,
        passed=passed,
        feedback=feedback,
    )


class ProgrammableRule(BaseRule):
    type: Literal["PROGRAMMABLE"] = "PROGRAMMABLE"
    question_types: frozenset[QuestionType] = frozenset({"TEXT", "NUMERIC"})
    code: str = Field(..., description="Code to evaluate the answer")
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
