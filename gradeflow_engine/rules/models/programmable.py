from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Discriminator, Field, computed_field

from ...questions.types import Answer, QuestionType
from ..executors import python
from ..result import Result
from .base import BaseRule, BaseSingleQuestionRule

ProgrammableMode = Literal["PASS_FAIL", "OUTPUT"]


TIME_LIMIT_S = 5


DEFAULT_PROGRAMMABLE_CODE = """# You have access to the following variables:
# - 'answer' variable contains the student's answer (can be str, float, list, or set)
# - any additional variables defined in 'parameters' (e.g., 'param1', 'param2', etc.)
# You must set the following variables:
# - 'output' (float): A number between 0 and 1 -- max_points multiplier (only used in OUTPUT mode)
# - 'passed' (bool): Whether the answer passed (only used in PASS_FAIL mode)
# - 'feedback' (str, optional): Feedback to provide to the student
# Example code:
passed = False
output = 0.0
feedback = str(answer)
"""


class IntParameter(BaseModel):
    dtype: Literal["Int"] = Field(default="Int", frozen=True, json_schema_extra={"readOnly": True})
    value: int


class FloatParameter(BaseModel):
    dtype: Literal["Float"] = Field(
        default="Float", frozen=True, json_schema_extra={"readOnly": True}
    )
    value: float


class StringParameter(BaseModel):
    dtype: Literal["String"] = Field(
        default="String", frozen=True, json_schema_extra={"readOnly": True}
    )
    value: str


class BooleanParameter(BaseModel):
    dtype: Literal["Boolean"] = Field(
        default="Boolean", frozen=True, json_schema_extra={"readOnly": True}
    )
    value: bool


class ListParameter(BaseModel):
    dtype: Literal["List"] = Field(
        default="List", frozen=True, json_schema_extra={"readOnly": True}
    )
    value: list[Parameter]


class DictParameter(BaseModel):
    dtype: Literal["Dict"] = Field(
        default="Dict", frozen=True, json_schema_extra={"readOnly": True}
    )
    value: dict[str, Parameter]


Parameter = Annotated[
    IntParameter
    | FloatParameter
    | StringParameter
    | BooleanParameter
    | ListParameter
    | DictParameter,
    Discriminator("dtype"),
]

ListParameter.model_rebuild()
DictParameter.model_rebuild()


def _unwrap_parameter(param: Parameter) -> Any:
    """Recursively convert a Parameter into a plain Python value."""
    if isinstance(param, (IntParameter, FloatParameter, StringParameter, BooleanParameter)):
        return param.value
    elif isinstance(param, ListParameter):
        return [_unwrap_parameter(item) for item in param.value]
    elif isinstance(param, DictParameter):
        return {key: _unwrap_parameter(val) for key, val in param.value.items()}
    else:
        raise TypeError(f"Unknown parameter type: {type(param)}")


@dataclass(frozen=True)
class ProgrammableResult:
    output: float
    passed: bool
    feedback: str


def evaluate(code: str, parameters: dict[str, Parameter], answer: Answer) -> ProgrammableResult:
    variables: dict[str, Any] = {
        "answer": answer,
    }
    for name, param in parameters.items():
        variables[name] = _unwrap_parameter(param)

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
    type: Literal["PROGRAMMABLE"] = Field(
        default="PROGRAMMABLE", frozen=True, json_schema_extra={"readOnly": True}
    )
    display_name: Literal["Programmable"] = Field(
        default="Programmable", frozen=True, json_schema_extra={"readOnly": True}
    )
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}),
        frozen=True,
        json_schema_extra={"readOnly": True},
    )
    code: str = Field(
        default=DEFAULT_PROGRAMMABLE_CODE,
        description="Code to evaluate the answer. "
        "Required variables: 'output', 'passed'. "
        "Optional variable: 'feedback'.",
    )
    parameters: dict[str, Parameter] = Field(
        default_factory=dict,
        description="Parameters that can be used in the code.",
    )
    mode: ProgrammableMode = Field(
        default="PASS_FAIL",
        description=(
            "Mode of evaluation: "
            "'PASS_FAIL' uses a boolean 'passed' variable, "
            "'OUTPUT' uses the 'output' variable (0-1) for scoring."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return (
            f"Custom code that uses {'`output`' if self.mode == 'OUTPUT' else '`passed`'} "
            "variable to determine score."
        )

    def _process_answer(self, answer: Answer) -> Result:
        result = evaluate(self.code, self.parameters, answer)
        return Result(
            output=result.output,
            passed=result.passed,
            feedback=result.feedback,
            rule=self.__class__.__name__,
        )


class ProgrammableQuestionRule(ProgrammableRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        if self.mode == "OUTPUT":
            return result.output * max_points
        elif self.mode == "PASS_FAIL":
            return max_points if result.passed else 0.0
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
