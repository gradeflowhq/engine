import pytest

from gradeflow_engine.exceptions import MissingAnswerError
from gradeflow_engine.questions.models import Question
from gradeflow_engine.questions.models.text import TextQuestion
from gradeflow_engine.questions.types import QuestionId
from gradeflow_engine.rules.models.programmable import (
    BooleanParameter,
    DictParameter,
    FloatParameter,
    IntParameter,
    ListParameter,
    ProgrammableMultiQuestionRule,
    ProgrammableQuestionRule,
    ProgrammableRule,
    StringParameter,
    _unwrap_parameter,
)
from gradeflow_engine.rules.result import Result

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


def test_programmable_parameters_infer_missing_dtype_from_value() -> None:
    rule = ProgrammableRule.model_validate(
        {
            "type": "PROGRAMMABLE",
            "parameters": {
                "target": {"value": 3},
                "suffix": {"value": "!"},
                "enabled": {"value": True},
                "threshold": {"value": 0.5},
                "labels": {"value": [{"value": "ok"}]},
                "mapping": {"value": {"expected": {"value": "yes"}}},
            },
        }
    )

    assert isinstance(rule.parameters["target"], IntParameter)
    assert isinstance(rule.parameters["suffix"], StringParameter)
    assert isinstance(rule.parameters["enabled"], BooleanParameter)
    assert isinstance(rule.parameters["threshold"], FloatParameter)
    assert isinstance(rule.parameters["labels"], ListParameter)
    assert isinstance(rule.parameters["mapping"], DictParameter)
    assert _unwrap_parameter(rule.parameters["mapping"]) == {"expected": "yes"}


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


def test_programmable_unwrap_parameter_rejects_unknown_value() -> None:
    with pytest.raises(TypeError):
        _unwrap_parameter(object())  # type: ignore[arg-type]


def test_programmable_question_rule_rejects_unknown_mode() -> None:
    malformed = ProgrammableQuestionRule.model_construct(question_id="Q1", mode="BAD")
    with pytest.raises(ValueError):
        malformed.compute_points(Result(output=1, passed=True, feedback="", rule="x"), 1)


# ===========================================================================
# ProgrammableMultiQuestionRule
# ===========================================================================


# ---------------------------------------------------------------------------
# PASS_FAIL mode — basic multi-question
# ---------------------------------------------------------------------------


def test_multi_pass_fail_all_pass() -> None:
    code = """
results = {}
for qid, answer in answer_map.items():
    results[qid] = {'passed': True, 'output': 1.0, 'feedback': f'{qid} ok'}
"""
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code=code, mode="PASS_FAIL"
    )
    qresults = rule.process_submission({"Q1": "a", "Q2": "b"}, {"Q1": 3.0, "Q2": 5.0})

    assert qresults["Q1"].passed is True
    assert qresults["Q1"].points == 3.0
    assert qresults["Q2"].passed is True
    assert qresults["Q2"].points == 5.0


def test_multi_pass_fail_some_fail() -> None:
    code = """
results = {
    'Q1': {'passed': True, 'output': 1.0, 'feedback': 'ok'},
    'Q2': {'passed': False, 'output': 0.0, 'feedback': 'wrong'},
}
"""
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code=code, mode="PASS_FAIL"
    )
    qresults = rule.process_submission({"Q1": "a", "Q2": "b"}, {"Q1": 2.0, "Q2": 4.0})

    assert qresults["Q1"].points == 2.0
    assert qresults["Q2"].points == 0.0


def test_multi_pass_fail_high_output_irrelevant_when_not_passed() -> None:
    code = """
results = {'Q1': {'passed': False, 'output': 0.99, 'feedback': 'nope'}}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1"], code=code, mode="PASS_FAIL")
    qresults = rule.process_submission({"Q1": "x"}, {"Q1": 10.0})

    assert qresults["Q1"].points == 0.0


# ---------------------------------------------------------------------------
# OUTPUT mode — multi-question
# ---------------------------------------------------------------------------


def test_multi_output_partial_scales_per_question() -> None:
    code = """
results = {
    'Q1': {'output': 0.5, 'passed': True, 'feedback': 'half'},
    'Q2': {'output': 0.25, 'passed': False, 'feedback': 'quarter'},
}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1", "Q2"], code=code, mode="OUTPUT")
    qresults = rule.process_submission({"Q1": "a", "Q2": "b"}, {"Q1": 10.0, "Q2": 8.0})

    assert qresults["Q1"].points == pytest.approx(5.0)
    assert qresults["Q2"].points == pytest.approx(2.0)


def test_multi_output_full_yields_max_points() -> None:
    code = """
results = {qid: {'output': 1.0, 'passed': True, 'feedback': 'full'} for qid in answer_map}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1", "Q2"], code=code, mode="OUTPUT")
    qresults = rule.process_submission({"Q1": "a", "Q2": "b"}, {"Q1": 3.0, "Q2": 7.0})

    assert qresults["Q1"].points == 3.0
    assert qresults["Q2"].points == 7.0


def test_multi_output_zero_yields_zero_points() -> None:
    code = """
results = {qid: {'output': 0.0, 'passed': False, 'feedback': 'zero'} for qid in answer_map}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1"], code=code, mode="OUTPUT")
    qresults = rule.process_submission({"Q1": "a"}, {"Q1": 5.0})

    assert qresults["Q1"].points == 0.0


# ---------------------------------------------------------------------------
# answer_map injection
# ---------------------------------------------------------------------------


def test_multi_answer_map_contains_only_target_questions() -> None:
    code = """
results = {}
for qid in answer_map:
    results[qid] = {'passed': True, 'output': 1.0, 'feedback': str(sorted(answer_map.keys()))}
"""
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q3"], code=code, mode="PASS_FAIL"
    )
    qresults = rule.process_submission({"Q1": "a", "Q2": "b", "Q3": "c"}, {"Q1": 1.0, "Q3": 1.0})

    # Feedback should show only Q1 and Q3, not Q2
    assert "Q2" not in qresults["Q1"].feedback
    assert "Q1" in qresults["Q1"].feedback
    assert "Q3" in qresults["Q1"].feedback


def test_multi_answer_values_are_passed_through() -> None:
    code = """
results = {}
for qid, ans in answer_map.items():
    results[qid] = {'passed': True, 'output': 1.0, 'feedback': str(ans)}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1"], code=code, mode="PASS_FAIL")
    qresults = rule.process_submission({"Q1": "hello"}, {"Q1": 1.0})

    assert qresults["Q1"].feedback == "hello"


def test_multi_numeric_answers_in_map() -> None:
    code = """
total = sum(answer_map.values())
results = {qid: {'output': v / total, 'passed': True, 'feedback': ''}
           for qid, v in answer_map.items()}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1", "Q2"], code=code, mode="OUTPUT")
    qresults = rule.process_submission({"Q1": 3, "Q2": 7}, {"Q1": 10.0, "Q2": 10.0})

    assert qresults["Q1"].points == pytest.approx(3.0)
    assert qresults["Q2"].points == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# Parameter injection — multi-question
# ---------------------------------------------------------------------------


def test_multi_parameters_accessible_in_code() -> None:
    code = """
results = {}
for qid, ans in answer_map.items():
    results[qid] = {
        'passed': ans == expected[qid],
        'output': 1.0 if ans == expected[qid] else 0.0,
        'feedback': f'expected {expected[qid]}',
    }
"""
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"],
        code=code,
        mode="PASS_FAIL",
        parameters={
            "expected": DictParameter(
                value={
                    "Q1": StringParameter(value="yes"),
                    "Q2": StringParameter(value="no"),
                }
            )
        },
    )
    qresults = rule.process_submission({"Q1": "yes", "Q2": "wrong"}, {"Q1": 1.0, "Q2": 1.0})

    assert qresults["Q1"].passed is True
    assert qresults["Q2"].passed is False


# ---------------------------------------------------------------------------
# Error handling — multi-question
# ---------------------------------------------------------------------------


def test_multi_runtime_error_returns_error_for_all_questions() -> None:
    code = "raise RuntimeError('multi boom')"
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code=code, mode="PASS_FAIL"
    )
    qresults = rule.process_submission({"Q1": "a", "Q2": "b"}, {"Q1": 5.0, "Q2": 5.0})

    for qid in ["Q1", "Q2"]:
        assert qresults[qid].passed is False
        assert qresults[qid].points == 0.0
        assert "Error during code execution" in qresults[qid].feedback
        assert "multi boom" in qresults[qid].feedback


def test_multi_syntax_error_returns_error_for_all_questions() -> None:
    code = "def ("
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1"], code=code, mode="PASS_FAIL")
    qresults = rule.process_submission({"Q1": "a"}, {"Q1": 1.0})

    assert qresults["Q1"].passed is False
    assert "Error during code execution" in qresults["Q1"].feedback


def test_multi_missing_answer_raises() -> None:
    code = "results = {}"
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code=code, mode="PASS_FAIL"
    )
    with pytest.raises(MissingAnswerError):
        rule.process_submission({"Q1": "a"}, {"Q1": 1.0, "Q2": 1.0})


def test_multi_missing_question_in_results_dict_gets_defaults() -> None:
    """Code returns results for Q1 but not Q2 — Q2 should get defaults."""
    code = """
results = {'Q1': {'passed': True, 'output': 1.0, 'feedback': 'ok'}}
"""
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code=code, mode="PASS_FAIL"
    )
    qresults = rule.process_submission({"Q1": "a", "Q2": "b"}, {"Q1": 2.0, "Q2": 3.0})

    assert qresults["Q1"].passed is True
    assert qresults["Q1"].points == 2.0
    assert qresults["Q2"].passed is False
    assert qresults["Q2"].points == 0.0


def test_multi_non_dict_result_for_question_gets_defaults() -> None:
    """Code returns a non-dict value for a question — should get defaults."""
    code = """
results = {'Q1': 'not a dict'}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1"], code=code, mode="PASS_FAIL")
    qresults = rule.process_submission({"Q1": "a"}, {"Q1": 1.0})

    assert qresults["Q1"].passed is False
    assert qresults["Q1"].points == 0.0


def test_multi_no_results_variable_gets_defaults() -> None:
    """Code sets no 'results' variable — all questions get defaults."""
    code = "x = 42"
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code=code, mode="PASS_FAIL"
    )
    qresults = rule.process_submission({"Q1": "a", "Q2": "b"}, {"Q1": 1.0, "Q2": 1.0})

    for qid in ["Q1", "Q2"]:
        assert qresults[qid].passed is False
        assert qresults[qid].points == 0.0


# ---------------------------------------------------------------------------
# Default max_points — multi-question
# ---------------------------------------------------------------------------


def test_multi_missing_max_points_defaults_to_one() -> None:
    code = """
results = {qid: {'passed': True, 'output': 1.0, 'feedback': ''} for qid in answer_map}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1"], code=code, mode="PASS_FAIL")
    # max_points_map does not contain Q1
    qresults = rule.process_submission({"Q1": "a"}, {})

    assert qresults["Q1"].points == 1.0
    assert qresults["Q1"].max_points == 1.0


def test_multi_zero_max_points_yields_zero() -> None:
    code = """
results = {qid: {'passed': True, 'output': 1.0, 'feedback': ''} for qid in answer_map}
"""
    rule = ProgrammableMultiQuestionRule(target_question_ids=["Q1"], code=code, mode="OUTPUT")
    qresults = rule.process_submission({"Q1": "a"}, {"Q1": 0.0})

    assert qresults["Q1"].points == 0.0


# ---------------------------------------------------------------------------
# Validation — multi-question
# ---------------------------------------------------------------------------


def test_multi_validate_questions_exist_all_present() -> None:
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code="results = {}", mode="PASS_FAIL"
    )
    errors = rule.validate_questions_exist({"Q1", "Q2", "Q3"})
    assert errors == []


def test_multi_validate_questions_exist_some_missing() -> None:
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2", "Q3"], code="results = {}", mode="PASS_FAIL"
    )
    errors = rule.validate_questions_exist({"Q1"})
    assert len(errors) == 2
    assert any("Q2" in e for e in errors)
    assert any("Q3" in e for e in errors)


def test_multi_validate_unique_no_duplicates() -> None:
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code="results = {}", mode="PASS_FAIL"
    )
    errors = rule.validate_unique_target_questions()
    assert errors == []


def test_multi_validate_unique_with_duplicates() -> None:
    rule = ProgrammableMultiQuestionRule.model_construct(
        target_question_ids=["Q1", "Q1", "Q2"],
        code="results = {}",
        mode="PASS_FAIL",
        type="PROGRAMMABLE_MULTI",
        display_name="Programmable (Multi)",
        question_types=frozenset({"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}),
        constraints=[],
        parameters={},
    )
    errors = rule.validate_unique_target_questions()
    assert len(errors) == 1
    assert "Q1" in errors[0]


def test_multi_validate_compatibility_all_compatible() -> None:
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code="results = {}", mode="PASS_FAIL"
    )
    question_map: dict[QuestionId, Question] = {"Q1": TextQuestion(), "Q2": TextQuestion()}
    errors = rule.validate_compatibility(question_map)
    assert errors == []


def test_multi_validate_compatibility_missing_question_skipped() -> None:
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code="results = {}", mode="PASS_FAIL"
    )
    question_map: dict[QuestionId, Question] = {"Q1": TextQuestion()}
    # Q2 not in map — should not error (existence validated elsewhere)
    errors = rule.validate_compatibility(question_map)
    assert errors == []


def test_multi_get_target_question_ids() -> None:
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2", "Q3"], code="results = {}", mode="PASS_FAIL"
    )
    assert rule.get_target_question_ids() == {"Q1", "Q2", "Q3"}


# ---------------------------------------------------------------------------
# description computed field — multi-question
# ---------------------------------------------------------------------------


def test_multi_description_pass_fail_mode() -> None:
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1", "Q2"], code="results = {}", mode="PASS_FAIL"
    )
    assert "`passed`" in rule.description
    assert "Q1" in rule.description
    assert "Q2" in rule.description


def test_multi_description_output_mode() -> None:
    rule = ProgrammableMultiQuestionRule(
        target_question_ids=["Q1"], code="results = {}", mode="OUTPUT"
    )
    assert "`output`" in rule.description
    assert "Q1" in rule.description


# ---------------------------------------------------------------------------
# Rejects unknown mode — multi-question
# ---------------------------------------------------------------------------


def test_multi_programmable_rejects_unknown_mode() -> None:
    rule = ProgrammableMultiQuestionRule.model_construct(
        target_question_ids=["Q1"],
        code="results = {'Q1': {'passed': True, 'output': 1.0, 'feedback': ''}}",
        mode="BAD",
        type="PROGRAMMABLE_MULTI",
        display_name="Programmable (Multi)",
        question_types=frozenset({"TEXT", "NUMERIC", "CHOICE", "MULTI_VALUED"}),
        constraints=[],
        parameters={},
    )
    with pytest.raises(ValueError):
        rule.process_submission({"Q1": "a"}, {"Q1": 1.0})
