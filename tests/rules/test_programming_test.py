from gradeflow_engine.rules.models.programming import (
    ProgrammingConfig,
    ProgrammingQuestionRule,
    ProgrammingRule,
    ProgrammingTestCase,
    evaluate_expected,
)


def test_programming_test_passes_simple_expression() -> None:
    # student code returns 2 + 2, expression should be str(output) compared to expected
    student_code = """
def add():
    return 2 + 2
"""
    testcases = [ProgrammingTestCase(expression="add()", expected="4")]
    rule = ProgrammingRule(testcases=testcases)
    result = rule.process_answer(student_code)

    assert result.passed is True
    assert "add()" in result.feedback


def test_programming_test_fails_wrong_output() -> None:
    student_code = """
def add():
    return 1 + 1
"""
    testcases = [ProgrammingTestCase(expression="add()", expected="4")]
    rule = ProgrammingRule(testcases=testcases)
    result = rule.process_answer(student_code)

    assert result.passed is False


def test_programming_test_runtime_error_raises() -> None:
    # Code that raises an error (undefined name)
    student_code = """
def f():
    return undefined_variable
"""
    testcases = [ProgrammingTestCase(expression="f()", expected="1")]
    rule = ProgrammingRule(testcases=testcases)

    result = rule.process_answer(student_code)

    assert result.passed is False
    assert "undefined_variable" in result.feedback


def test_programming_question_rule_points_partial_any_all() -> None:
    student_code = """
def f():
    return 1
def g():
    return 2
"""
    testcases = [
        ProgrammingTestCase(expression="f()", expected="1"),
        ProgrammingTestCase(expression="g()", expected="2"),
    ]

    # ALL mode: both must pass for full points
    q_all = ProgrammingQuestionRule(question_id="q", testcases=testcases, mode="ALL")
    qresult = q_all.process_submission({"q": student_code}, {"q": 5.0})["q"]
    assert qresult.points == 5.0

    # ANY mode: at least one passes (here both pass so full points)
    q_any = ProgrammingQuestionRule(question_id="q", testcases=testcases, mode="ANY")
    qresult = q_any.process_submission({"q": student_code}, {"q": 5.0})["q"]
    assert qresult.points == 5.0

    # PARTIAL: should get proportional credit (here 2/2)
    q_partial = ProgrammingQuestionRule(question_id="q", testcases=testcases, mode="PARTIAL")
    qresult = q_partial.process_submission({"q": student_code}, {"q": 6.0})["q"]
    assert qresult.points == 6.0


def test_programming_expected_evaluation_and_description_edges() -> None:
    assert (
        evaluate_expected(
            ProgrammingTestCase(expression="x", expected="undefined_name"),
            ProgrammingConfig(),
        )
        == "undefined_name"
    )
    assert (
        "Code must pass"
        in ProgrammingRule(
            testcases=[ProgrammingTestCase(expression="x", expected="1")]
        ).description
    )
