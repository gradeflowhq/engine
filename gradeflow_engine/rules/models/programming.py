from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..executors.restricted_python import safe_exec
from ..result import Result
from ..types import CompletenessAggregation
from .base import BaseRule, BaseSingleQuestionRule

ProgrammingLanguage = Literal["python"]  # Extendable to other languages in the future


class ProgrammingTestCase(BaseModel):
    expression: str = Field(..., description="Input for the test case")
    expected: str = Field(..., description="Expected output for the test case")


@dataclass(frozen=True)
class ProgrammingTestCaseResult:
    output: Any
    passed: bool


class ProgrammingConfig(BaseModel):
    prepend_code: str = Field(
        default="",
        description="Code to prepend to the student's answer before running test cases",
    )
    append_code: str = Field(
        default="",
        description="Code to append to the student's answer after running test cases",
    )
    indent: int = Field(
        default=0,
        description="Number of spaces to indent the student's code when embedding it",
    )
    memory_limit: int = Field(
        default=64,
        description="Memory limit in megabytes for code execution",
    )
    time_limit: int = Field(
        default=5,
        description="Time limit in seconds for code execution",
    )


def assemble_code(prepend: str, student_code: str, append: str, indent: int) -> str:
    indented_code = "\n".join(
        (" " * indent) + line if line.strip() else line for line in student_code.splitlines()
    )
    return f"{prepend}\n{indented_code}\n{append}"


def evaluate(
    code: str, testcase: ProgrammingTestCase, config: ProgrammingConfig
) -> ProgrammingTestCaseResult:
    # Ensure expected is represented as a Python string literal when inlined
    code_with_testcase = f"""{code}
output = {testcase.expression}
passed = str(output) == {testcase.expected!r}
result = {{'output': output, 'passed': passed}}
"""
    local_vars: dict[str, Any] = {}
    try:
        safe_exec(
            code_with_testcase,
            local_vars,
            memory_limit=config.memory_limit,
            time_limit=config.time_limit,
        )
    except Exception as e:
        return ProgrammingTestCaseResult(output=str(e), passed=False)

    result: dict[str, Any] = local_vars.get("result", {"output": None, "passed": False})
    return ProgrammingTestCaseResult(output=result["output"], passed=result["passed"])


class ProgrammingRule(BaseRule):
    type: Literal["PROGRAMMING"] = "PROGRAMMING"
    question_types: frozenset[QuestionType] = frozenset({"TEXT", "NUMERIC"})
    testcases: list[ProgrammingTestCase] = Field(
        ..., description="List of test cases to run against the code"
    )
    language: ProgrammingLanguage = Field(
        default="python",
        description="Programming language of the code to be tested",
    )
    config: ProgrammingConfig = Field(
        default_factory=ProgrammingConfig,
        description="Configuration for code testing",
    )
    mode: CompletenessAggregation = Field(
        default="ALL",
        description=(
            "Mode of test case evaluation: "
            "'ALL' requires all test cases to pass, "
            "'ANY' requires at least one to pass, "
            "'PARTIAL' gives credit for each test case passed."
        ),
    )

    def _process_answer(self, answer: Answer) -> Result:
        code = assemble_code(
            prepend=self.config.prepend_code,
            student_code=str(answer),
            append=self.config.append_code,
            indent=self.config.indent,
        )
        results = [evaluate(code, testcase, self.config) for testcase in self.testcases]
        passed_list = [result.passed for result in results]
        output = output_fn(passed_list, mode=self.mode)
        passed = passed_fn(passed_list, mode=self.mode)
        feedback = ", ".join(
            (
                f"Test case {testcase.expression}: Output: {result.output}, "
                f"Expected: {testcase.expected}."
                for testcase, result in zip(self.testcases, results, strict=True)
            )
        )

        return Result(
            output=output,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class ProgrammingQuestionRule(ProgrammingRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result) -> float:
        return points_fn(result, mode=self.mode, max_points=self.max_points)
