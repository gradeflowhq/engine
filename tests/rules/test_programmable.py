import pytest

from gradeflow_engine.rules.models.programmable import (
    BooleanParameter,
    DictParameter,
    FloatParameter,
    IntParameter,
    ListParameter,
    ProgrammableQuestionRule,
    ProgrammableRule,
    StringParameter,
)

# ---------------------------------------------------------------------------
# PASS_FAIL mode — basic
# ---------------------------------------------------------------------------


def test_programmable_pass_fail_mode_passes() -> None:
    code = """
passed = True
output = 1.0
feedback = 'ok'
"""
    rule = ProgrammableRule(code=code, mode="PASS_FAIL")
    result = rule.process_answer("any answer")

    assert result.passed is True
    assert result.output == 1.0
    assert "ok" in result.feedback


def test_programmable_pass_fail_mode_fails() -> None:
    code = """
passed = False
output = 0.0
feedback = 'failed'
"""
    rule = ProgrammableRule(code=code, mode="PASS_FAIL")
    result = rule.process_answer("any answer")

    assert result.passed is False
    assert result.output == 0.0
    assert "failed" in result.feedback


# ---------------------------------------------------------------------------
# OUTPUT mode — basic
# ---------------------------------------------------------------------------


def test_programmable_output_mode_scoring_uses_output_multiplier() -> None:
    code = """
output = 0.6
passed = False  # should not matter for scoring in OUTPUT mode
feedback = 'partial'
"""
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="OUTPUT")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 10.0})["q"]

    assert qresult.points == 6.0
    assert qresult.output == 0.6
    assert "partial" in qresult.feedback


def test_programmable_pass_fail_mode_scoring_uses_passed_only() -> None:
    code = """
passed = True
output = 0.0  # should not matter for scoring in PASS_FAIL mode
feedback = 'good'
"""
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="PASS_FAIL")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 4.0})["q"]

    assert qresult.points == 4.0
    assert qresult.passed is True


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_programmable_runtime_error_returns_feedback_and_fails() -> None:
    code = """
raise RuntimeError('boom')
"""
    rule = ProgrammableRule(code=code)
    result = rule.process_answer("ignored")

    assert result.passed is False
    assert result.output == 0.0
    assert "Error during code execution" in result.feedback
    assert "boom" in result.feedback


def test_programmable_syntax_error_returns_feedback_and_fails() -> None:
    code = "def ("  # deliberate syntax error
    rule = ProgrammableRule(code=code)
    result = rule.process_answer("ignored")

    assert result.passed is False
    assert result.output == 0.0
    assert "Error during code execution" in result.feedback


# ---------------------------------------------------------------------------
# Answer variable injection
# ---------------------------------------------------------------------------


def test_programmable_uses_answer_variable() -> None:
    code = """
if answer == 'yes':
    passed = True
    output = 1.0
else:
    passed = False
    output = 0.0
feedback = 'checked'
"""
    rule = ProgrammableRule(code=code)
    res_yes = rule.process_answer("yes")
    res_no = rule.process_answer("no")

    assert res_yes.passed is True
    assert res_yes.output == 1.0
    assert res_no.passed is False
    assert res_no.output == 0.0


def test_programmable_uses_numeric_answer() -> None:
    code = """
passed = answer == 42
output = 1.0 if passed else 0.0
feedback = 'numeric check'
"""
    rule = ProgrammableRule(code=code)
    assert rule.process_answer(42).passed is True
    assert rule.process_answer(0).passed is False


def test_programmable_uses_list_answer() -> None:
    code = """
passed = set(answer) == {1, 2, 3}
output = 1.0 if passed else 0.0
feedback = 'list check'
"""
    rule = ProgrammableRule(code=code)
    assert rule.process_answer([1, 2, 3]).passed is True
    assert rule.process_answer([1, 2]).passed is False


def test_programmable_uses_set_answer() -> None:
    code = """
passed = answer == {'a', 'b'}
output = 1.0 if passed else 0.0
feedback = 'set check'
"""
    rule = ProgrammableRule(code=code)
    assert rule.process_answer({"a", "b"}).passed is True
    assert rule.process_answer({"a"}).passed is False


# ---------------------------------------------------------------------------
# Default variable values when code sets nothing
# ---------------------------------------------------------------------------


def test_programmable_defaults_when_vars_absent() -> None:
    code = """
# no vars set
"""
    rule = ProgrammableRule(code=code)
    res = rule.process_answer("anything")

    assert res.output == 0.0
    assert res.passed is False
    assert res.feedback  # should be some non-empty default message


# ---------------------------------------------------------------------------
# Parameter injection — all supported types
# ---------------------------------------------------------------------------


def test_programmable_int_parameter_injected() -> None:
    code = """
passed = (answer == target)
output = 1.0 if passed else 0.0
feedback = f"answer={answer}{suffix}, target={target}"
"""
    rule = ProgrammableRule(
        code=code,
        parameters={
            "target": IntParameter(value=3),
            "suffix": StringParameter(value="!"),
        },
    )

    res_ok = rule.process_answer(3)
    res_bad = rule.process_answer(4)

    assert res_ok.passed is True
    assert res_ok.output == 1.0
    assert "answer=3!" in res_ok.feedback
    assert "target=3" in res_ok.feedback

    assert res_bad.passed is False
    assert res_bad.output == 0.0


def test_programmable_float_parameter_injected() -> None:
    code = """
passed = abs(answer - threshold) < 0.01
output = 1.0 if passed else 0.0
feedback = 'float check'
"""
    rule = ProgrammableRule(
        code=code,
        parameters={"threshold": FloatParameter(value=3.14)},
    )

    assert rule.process_answer(3.14).passed is True
    assert rule.process_answer(0.0).passed is False


def test_programmable_boolean_parameter_injected() -> None:
    # bool is not a valid Answer type — validate_answer_type rejects it before
    # the code runs. Use a string answer and compare it against a derived value
    # so the BooleanParameter is still meaningfully exercised.
    code = """
passed = (answer == "yes") == flag
output = 1.0 if passed else 0.0
feedback = 'bool check'
"""
    rule = ProgrammableRule(
        code=code,
        parameters={"flag": BooleanParameter(value=True)},
    )

    # "yes" == "yes" → True, which equals flag (True) → passed
    assert rule.process_answer("yes").passed is True
    # "no" == "yes" → False, which does not equal flag (True) → not passed
    assert rule.process_answer("no").passed is False


def test_programmable_list_parameter_injected() -> None:
    code = """
passed = answer in allowed
output = 1.0 if passed else 0.0
feedback = 'list param check'
"""
    rule = ProgrammableRule(
        code=code,
        parameters={
            "allowed": ListParameter(
                value=[StringParameter(value="foo"), StringParameter(value="bar")]
            )
        },
    )

    assert rule.process_answer("foo").passed is True
    assert rule.process_answer("baz").passed is False


def test_programmable_dict_parameter_injected() -> None:
    code = """
passed = answer == mapping['key']
output = 1.0 if passed else 0.0
feedback = 'dict param check'
"""
    rule = ProgrammableRule(
        code=code,
        parameters={"mapping": DictParameter(value={"key": StringParameter(value="expected")})},
    )

    assert rule.process_answer("expected").passed is True
    assert rule.process_answer("wrong").passed is False


def test_programmable_nested_list_and_dict_parameters_unwrap_correctly() -> None:
    # A ListParameter whose elements are DictParameters — verifies full recursion
    # through _unwrap_parameter.
    code = """
passed = any(item['match'] == answer for item in options)
output = 1.0 if passed else 0.0
feedback = 'nested check'
"""
    rule = ProgrammableRule(
        code=code,
        parameters={
            "options": ListParameter(
                value=[
                    DictParameter(value={"match": StringParameter(value="alpha")}),
                    DictParameter(value={"match": StringParameter(value="beta")}),
                ]
            )
        },
    )

    assert rule.process_answer("alpha").passed is True
    assert rule.process_answer("beta").passed is True
    assert rule.process_answer("gamma").passed is False


def test_programmable_nested_dict_of_lists_unwraps_correctly() -> None:
    # A DictParameter whose values are ListParameters — verifies the other
    # direction of nesting through _unwrap_parameter.
    code = """
passed = answer in lookup['valid']
output = 1.0 if passed else 0.0
feedback = 'nested dict-of-list check'
"""
    rule = ProgrammableRule(
        code=code,
        parameters={
            "lookup": DictParameter(
                value={
                    "valid": ListParameter(
                        value=[
                            StringParameter(value="x"),
                            StringParameter(value="y"),
                        ]
                    )
                }
            )
        },
    )

    assert rule.process_answer("x").passed is True
    assert rule.process_answer("y").passed is True
    assert rule.process_answer("z").passed is False


# ---------------------------------------------------------------------------
# OUTPUT mode — boundary values and scoring edge cases
# ---------------------------------------------------------------------------


def test_output_mode_zero_output_yields_zero_points() -> None:
    code = "output = 0.0\npassed = True\n"
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="OUTPUT")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 5.0})["q"]

    assert qresult.points == 0.0


def test_output_mode_full_output_yields_max_points() -> None:
    code = "output = 1.0\npassed = False\n"
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="OUTPUT")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 5.0})["q"]

    assert qresult.points == 5.0


def test_output_mode_partial_output_scales_correctly() -> None:
    code = "output = 0.25\npassed = False\n"
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="OUTPUT")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 8.0})["q"]

    assert qresult.points == pytest.approx(2.0)


@pytest.mark.parametrize(
    "code, expected_points",
    [
        ("output = 0.0\npassed = True\n", 0.0),
        ("output = 1.0\npassed = False\n", 5.0),
    ],
)
def test_output_mode_points_ignore_passed(code: str, expected_points: float) -> None:
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="OUTPUT")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 5.0})["q"]
    assert qresult.points == expected_points


# ---------------------------------------------------------------------------
# PASS_FAIL mode — scoring edge cases
# ---------------------------------------------------------------------------


def test_pass_fail_mode_high_output_still_zero_when_not_passed() -> None:
    """output is irrelevant in PASS_FAIL mode — only passed matters."""
    code = "output = 0.99\npassed = False\n"
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="PASS_FAIL")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 10.0})["q"]

    assert qresult.points == 0.0


def test_pass_fail_mode_zero_max_points_yields_zero() -> None:
    code = "passed = True\noutput = 1.0\n"
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="PASS_FAIL")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 0.0})["q"]

    assert qresult.points == 0.0


def test_output_mode_zero_max_points_yields_zero() -> None:
    code = "output = 1.0\npassed = True\n"
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="OUTPUT")
    qresult = qrule.process_submission({"q": "ignored"}, {"q": 0.0})["q"]

    assert qresult.points == 0.0


# ---------------------------------------------------------------------------
# Output variable coercion
# ---------------------------------------------------------------------------


def test_non_numeric_output_variable_is_coerced_or_errors() -> None:
    """If code sets output to a string that can be cast to float, it should work."""
    code = "output = '0.5'\npassed = True\n"
    rule = ProgrammableRule(code=code)
    result = rule.process_answer("anything")

    # float('0.5') == 0.5, so coercion should succeed
    assert result.output == pytest.approx(0.5)


def test_non_castable_output_variable_returns_error() -> None:
    code = "output = 'not_a_number'\npassed = True\n"
    rule = ProgrammableRule(code=code)
    result = rule.process_answer("anything")

    assert result.passed is False
    assert result.output == 0.0
    assert "Error retrieving result variables" in result.feedback


# ---------------------------------------------------------------------------
# description computed field
# ---------------------------------------------------------------------------


def test_description_pass_fail_mode() -> None:
    rule = ProgrammableRule(mode="PASS_FAIL")
    assert "`passed`" in rule.description


def test_description_output_mode() -> None:
    rule = ProgrammableRule(mode="OUTPUT")
    assert "`output`" in rule.description
