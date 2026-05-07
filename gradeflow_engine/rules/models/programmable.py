from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Discriminator, Field, computed_field

from ...exceptions import MissingAnswerError
from ...questions.models import Question
from ...questions.types import Answer, QuestionId, QuestionType
from ..executors import python
from ..result import QuestionResult, Result
from ..types import RuleValidationError
from .base import (
    DEFAULT_MAX_POINTS,
    BaseMultiQuestionRule,
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)

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

DEFAULT_MULTI_PROGRAMMABLE_CODE = """# You have access to the following variables:
# - 'answer_map' dict mapping question_id -> student's answer for each target question
# - any additional variables defined in 'parameters' (e.g., 'param1', 'param2', etc.)
# You must set the following variable:
# - 'results' (dict): A dict mapping question_id -> dict with keys:
#     - 'output' (float): A number between 0 and 1 -- max_points multiplier (OUTPUT mode)
#     - 'passed' (bool): Whether the answer passed (only used in PASS_FAIL mode)
#     - 'feedback' (str, optional): Feedback to provide to the student
# Example code:
results = {}
for qid, answer in answer_map.items():
    results[qid] = {
        'output': 0.0,
        'passed': False,
        'feedback': str(answer),
    }
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
    value: list["Parameter"]


class DictParameter(BaseModel):
    dtype: Literal["Dict"] = Field(
        default="Dict", frozen=True, json_schema_extra={"readOnly": True}
    )
    value: dict[str, "Parameter"]


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


def _unwrap_parameters(parameters: dict[str, Parameter]) -> dict[str, Any]:
    """Unwrap all parameters into plain Python values."""
    return {name: _unwrap_parameter(param) for name, param in parameters.items()}


@dataclass(frozen=True)
class ProgrammableResult:
    output: float
    passed: bool
    feedback: str


def _run_code(code: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Run code in subprocess and return updated variables. Raises on failure."""
    python.run(code, variables, time_limit_s=TIME_LIMIT_S)
    return variables


def _extract_single_result(variables: dict[str, Any]) -> ProgrammableResult:
    """Extract output/passed/feedback from executed variables."""
    return ProgrammableResult(
        output=float(variables.get("output", 0.0)),
        passed=bool(variables.get("passed", False)),
        feedback=str(variables.get("feedback", "No feedback provided.")),
    )


def _error_result(error: Exception) -> ProgrammableResult:
    return ProgrammableResult(
        output=0.0, passed=False, feedback=f"Error during code execution: {error}"
    )


def evaluate(code: str, parameters: dict[str, Parameter], answer: Answer) -> ProgrammableResult:
    variables: dict[str, Any] = {"answer": answer, **_unwrap_parameters(parameters)}
    try:
        _run_code(code, variables)
    except Exception as e:
        return _error_result(e)
    try:
        return _extract_single_result(variables)
    except Exception as e:
        return ProgrammableResult(
            output=0.0, passed=False, feedback=f"Error retrieving result variables: {e}"
        )


def _extract_multi_results(
    variables: dict[str, Any], target_question_ids: list[QuestionId]
) -> dict[QuestionId, ProgrammableResult]:
    """Extract per-question results from executed variables."""
    raw_results: dict[str, Any] = variables.get("results", {})
    per_question: dict[QuestionId, ProgrammableResult] = {}
    for qid in target_question_ids:
        qid_raw = raw_results.get(qid, {})
        if not isinstance(qid_raw, dict):
            qid_raw = {}
        try:
            per_question[qid] = ProgrammableResult(
                output=float(qid_raw.get("output", 0.0)),
                passed=bool(qid_raw.get("passed", False)),
                feedback=str(qid_raw.get("feedback", "No feedback provided.")),
            )
        except Exception as e:
            per_question[qid] = ProgrammableResult(
                output=0.0, passed=False, feedback=f"Error retrieving result for {qid}: {e}"
            )
    return per_question


def evaluate_multi(
    code: str,
    parameters: dict[str, Parameter],
    answer_map: dict[QuestionId, Answer],
    target_question_ids: list[QuestionId],
) -> dict[QuestionId, ProgrammableResult]:
    """Execute code with an answer_map and return per-question results."""
    variables: dict[str, Any] = {"answer_map": dict(answer_map), **_unwrap_parameters(parameters)}
    try:
        _run_code(code, variables)
    except Exception as e:
        error = _error_result(e)
        return dict.fromkeys(target_question_ids, error)
    return _extract_multi_results(variables, target_question_ids)


def _compute_programmable_points(
    mode: ProgrammableMode, result: ProgrammableResult, max_points: float
) -> float:
    if mode == "OUTPUT":
        return result.output * max_points
    elif mode == "PASS_FAIL":
        return max_points if result.passed else 0.0
    else:
        raise ValueError(f"Unknown mode: {mode}")


class ProgrammableRule(BaseRule):
    type: Literal["PROGRAMMABLE"] = rule_type_field("PROGRAMMABLE")
    display_name: Literal["Programmable"] = rule_display_name_field("Programmable")
    question_types: frozenset[QuestionType] = rule_question_types_field(
        {"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}
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
        return _compute_programmable_points(
            self.mode,
            ProgrammableResult(
                output=result.output if isinstance(result.output, float) else float(result.output),
                passed=result.passed,
                feedback=result.feedback,
            ),
            max_points,
        )


class ProgrammableMultiQuestionRule(BaseMultiQuestionRule):
    type: Literal["PROGRAMMABLE_MULTI"] = rule_type_field("PROGRAMMABLE_MULTI")
    display_name: Literal["Programmable"] = rule_display_name_field("Programmable")
    question_types: frozenset[QuestionType] = rule_question_types_field(
        {"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}
    )
    target_question_ids: list[QuestionId] = Field(
        ...,
        min_length=1,
        description="List of question IDs this rule targets.",
    )
    code: str = Field(
        default=DEFAULT_MULTI_PROGRAMMABLE_CODE,
        description="Code to evaluate the answer_map. "
        "Required variable: 'results' (dict mapping question_id -> "
        "dict with 'output', 'passed', and optionally 'feedback').",
    )
    parameters: dict[str, Parameter] = Field(
        default_factory=dict,
        description="Parameters that can be used in the code.",
    )
    mode: ProgrammableMode = Field(
        default="PASS_FAIL",
        description=(
            "Mode of evaluation: "
            "'PASS_FAIL' uses 'passed' per question, "
            "'OUTPUT' uses 'output' (0-1) per question for scoring."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        qids = ", ".join(self.target_question_ids)
        return (
            f"Custom multi-question code targeting [{qids}] that uses "
            f"{'`output`' if self.mode == 'OUTPUT' else '`passed`'} "
            "per question to determine scores."
        )

    def get_target_question_ids(self) -> set[QuestionId]:
        return set(self.target_question_ids)

    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        return [
            f"Question ID {qid} does not exist in the assessment."
            for qid in self.target_question_ids
            if qid not in question_ids
        ]

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        seen: set[QuestionId] = set()
        errors: list[RuleValidationError] = []
        for qid in self.target_question_ids:
            if qid in seen:
                errors.append(
                    f"Duplicate question ID {qid} in target_question_ids of {self.type} rule."
                )
            seen.add(qid)
        return errors

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        return [
            f"Rule of type {self.type} is not compatible with "
            f"question type {question_map[qid].type} for question {qid}."
            for qid in self.target_question_ids
            if qid in question_map and question_map[qid].type not in self.question_types
        ]

    def process_submission(
        self,
        answer_map: dict[QuestionId, Answer],
        max_points_map: dict[QuestionId, float],
    ) -> dict[QuestionId, QuestionResult]:
        scoped_answer_map: dict[QuestionId, Answer] = {}
        for qid in self.target_question_ids:
            if qid not in answer_map:
                raise MissingAnswerError(qid)
            scoped_answer_map[qid] = answer_map[qid]

        results = evaluate_multi(
            self.code, self.parameters, scoped_answer_map, self.target_question_ids
        )

        question_results: dict[QuestionId, QuestionResult] = {}
        for qid in self.target_question_ids:
            prog_result = results[qid]
            max_points = max_points_map.get(qid, DEFAULT_MAX_POINTS)
            question_results[qid] = QuestionResult(
                output=prog_result.output,
                passed=prog_result.passed,
                feedback=prog_result.feedback,
                rule=self.__class__.__name__,
                points=_compute_programmable_points(self.mode, prog_result, max_points),
                max_points=max_points,
            )
        return question_results
