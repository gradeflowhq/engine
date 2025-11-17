from gradeflow_engine.rules.models.programmable import (
    ProgrammableQuestionRule,
    ProgrammableRule,
)


def test_programmable_pass_fail_mode_passes() -> None:
    # code should set `passed = True` to give full credit in PASS_FAIL mode
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


def test_programmable_output_mode_scoring() -> None:
    # OUTPUT mode uses `output` (0.0-1.0) to compute points
    code = """
output = 0.6
passed = output >= 0.5
feedback = 'partial'
"""
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="OUTPUT", max_points=10.0)
    qresult = qrule.process_submission({"q": "ignored"})

    assert qresult.points == 6.0


def test_programmable_runtime_error_returns_feedback() -> None:
    # runtime error should produce a Result with passed False.
    # feedback should contain the error message
    code = """
raise RuntimeError('boom')
"""
    rule = ProgrammableRule(code=code)
    result = rule.process_answer("ignored")

    assert result.passed is False
    assert "Error during code execution" in result.feedback


def test_programmable_question_rule_pass_fail_points() -> None:
    # PASS_FAIL question rule should award full points when passed is True
    code = """
passed = True
output = 1.0
feedback = 'good'
"""
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="PASS_FAIL", max_points=4.0)
    qresult = qrule.process_submission({"q": "ignored"})

    assert qresult.points == 4.0


def test_programmable_uses_answer_variable() -> None:
    # The code can inspect `answer` provided by the system
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
    assert res_no.passed is False


def test_programmable_output_bounds_and_defaults() -> None:
    # Ensure that OUTPUT mode respects values (0.0-1.0) and defaults when variables absent
    code = """
output = 0.0
"""
    qrule = ProgrammableQuestionRule(question_id="q", code=code, mode="OUTPUT", max_points=5.0)
    qresult = qrule.process_submission({"q": "ignored"})
    assert qresult.points == 0.0

    # If code doesn't set any variables, defaults should be used (output 0.0, passed False)
    code2 = """\n# no vars set\n"""
    rule2 = ProgrammableRule(code=code2)
    res2 = rule2.process_answer("anything")
    assert res2.output == 0.0
    assert res2.passed is False
