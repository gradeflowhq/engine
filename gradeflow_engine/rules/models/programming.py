from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field

from ...questions.types import Answer, QuestionType
from ..aggregations.completeness import output_fn, passed_fn, points_fn
from ..executors import python
from ..result import Result
from ..types import CompletenessAggregation
from .base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)

ProgrammingLanguage = Literal["python"]  # Extendable to other languages in the future


class ProgrammingTestCase(BaseModel):
    expression: str = Field(..., description="Input for the test case")
    expected: str = Field(..., description="Expected output for the test case")


@dataclass(frozen=True)
class ProgrammingTestCaseResult:
    output: Any
    expected: Any
    passed: bool


class ProgrammingConfig(BaseModel):
    prepend_code: str = Field(
        default="",
        description="Code to prepend to the student's answer",
    )
    append_code: str = Field(
        default="",
        description="Code to append to the student's answer",
    )
    indent: int = Field(
        default=0,
        description="Number of spaces to indent the student's code when embedding it",
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


def evaluate_expected(testcase: ProgrammingTestCase, config: ProgrammingConfig) -> str | None:
    code_with_expected = f"""{config.prepend_code}\nTrue
{config.append_code}
expected = {testcase.expected}
"""
    variables: dict[str, Any] = {}
    try:
        python.run(code_with_expected, variables, time_limit_s=config.time_limit)
    except Exception:
        return testcase.expected
    return str(variables.get("expected", None))


def evaluate(
    code: str, testcase: ProgrammingTestCase, config: ProgrammingConfig
) -> ProgrammingTestCaseResult:
    code_with_testcase = f"""{code}
output = {testcase.expression}
expected = {testcase.expected}
passed = output == expected
result = {{'output': output, 'expected': expected, 'passed': passed}}
"""
    variables: dict[str, Any] = {}
    try:
        python.run(code_with_testcase, variables, time_limit_s=config.time_limit)
    except Exception as e:
        return ProgrammingTestCaseResult(output=str(e), expected=testcase.expected, passed=False)

    result: dict[str, Any] = variables.get(
        "result", {"output": None, "expected": None, "passed": False}
    )
    return ProgrammingTestCaseResult(
        output=result["output"], expected=result["expected"], passed=result["passed"]
    )


class ProgrammingRule(BaseRule):
    type: Literal["PROGRAMMING"] = rule_type_field("PROGRAMMING")
    display_name: Literal["Programming"] = rule_display_name_field("Programming")
    question_types: frozenset[QuestionType] = rule_question_types_field({"TEXT"})
    testcases: list[ProgrammingTestCase] = Field(
        ..., min_length=1, description="List of test cases to run against the code"
    )
    language: ProgrammingLanguage = Field(
        default="python",
        description="Programming language of the code to be tested",
    )
    config: ProgrammingConfig = Field(
        default_factory=ProgrammingConfig,
        description="Configuration for code testing",
    )
    show_evaluated_expected: bool = Field(
        default=True,
        description="Whether to show the evaluated expected output in feedback",
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def description(self) -> str:
        return "Code must pass:\n" + "\n".join(
            f"Test Case {i + 1}: Expression `{testcase.expression}` "
            f"evaluates to `{testcase.expected}`."
            for i, testcase in enumerate(self.testcases)
        )

    def _process_answer(self, answer: Answer) -> Result:
        code = assemble_code(
            prepend=self.config.prepend_code,
            student_code=str(answer),
            append=self.config.append_code,
            indent=self.config.indent,
        )
        expected_list = [evaluate_expected(testcase, self.config) for testcase in self.testcases]
        results = [evaluate(code, testcase, self.config) for testcase in self.testcases]
        passed_list = [result.passed for result in results]
        output = output_fn(passed_list, mode=self.mode)
        passed = passed_fn(passed_list, mode=self.mode)
        feedback = "\n".join(
            (
                f"[Test Case {i + 1}]\n"
                f"Expression: {testcase.expression}\n"
                f"Output: {result.output}\n"
                f"Expected: {expected if self.show_evaluated_expected else testcase.expected}\n"
                for i, (testcase, result, expected) in enumerate(
                    zip(self.testcases, results, expected_list, strict=True)
                )
            )
        )

        return Result(
            output=output,
            passed=passed,
            feedback=feedback,
            rule=self.__class__.__name__,
        )


class ProgrammingQuestionRule(ProgrammingRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return points_fn(result, mode=self.mode, max_points=max_points)
