import pytest

from gradeflow_engine.questions.models.numeric import NumericQuestion
from gradeflow_engine.questions.models.text import TextQuestion
from gradeflow_engine.rules.models.number_equal import (
    NumberEqualConfig,
    NumberEqualQuestionRule,
    NumberEqualRule,
)


def test_number_equal_exact_int_and_float_match() -> None:
    # approximate=True by default, but exact equality should also pass
    rule = NumberEqualRule(answers=[42, 3.5], config=NumberEqualConfig(approximate=False))
    res_int = rule.process_answer(42)
    res_float = rule.process_answer(3.5)

    assert res_int.passed is True and res_int.output is True
    assert "42 is correct" in res_int.feedback

    assert res_float.passed is True and res_float.output is True
    assert "3.5 is correct" in res_float.feedback


def test_number_equal_approximate_within_tolerance_passes() -> None:
    rule = NumberEqualRule(answers=[1.0], config=NumberEqualConfig(tolerance=1e-3))
    res = rule.process_answer(1.0005)
    assert res.passed is True and res.output is True
    assert "approximately correct" in res.feedback
    assert "(within tolerance of 0.001)" in res.feedback


def test_number_equal_outside_tolerance_fails() -> None:
    rule = NumberEqualRule(answers=[1.0], config=NumberEqualConfig(tolerance=1e-6))
    res = rule.process_answer(1.001)
    assert res.passed is False and res.output is False
    assert "Incorrect answer." in res.feedback
    assert "approximately" in res.feedback  # indicates approximate mode in feedback
    assert "(within a tolerance of 1e-06)" in res.feedback


def test_number_equal_multiple_answers_any_match() -> None:
    rule = NumberEqualRule(answers=[10, 20, 30], config=NumberEqualConfig(approximate=False))
    assert rule.process_answer(20).passed is True
    assert rule.process_answer(25).passed is False


def test_number_equal_question_rule_points() -> None:
    qrule = NumberEqualQuestionRule(question_id="Q", answers=[2.0], max_points=3.0)
    res_pass = qrule.process_submission({"Q": 2.0000001})  # within default tolerance 1e-6 -> pass
    assert res_pass.passed is True
    assert res_pass.points == 3.0
    assert res_pass.max_points == 3.0
    assert res_pass.question_id == "Q"

    res_fail = qrule.process_submission({"Q": 2.01})
    assert res_fail.passed is False
    assert res_fail.points == 0.0


def test_number_equal_question_rule_missing_answer_raises() -> None:
    qrule = NumberEqualQuestionRule(
        question_id="QX", answers=[1], config=NumberEqualConfig(approximate=False)
    )
    with pytest.raises(ValueError):
        qrule.process_submission({})


def test_number_equal_non_numeric_asserts() -> None:
    rule = NumberEqualRule(answers=[1.0], config=NumberEqualConfig(approximate=False))
    # Non-numeric should trigger the assertion in _process_answer
    with pytest.raises(TypeError):
        _ = rule.process_answer("not-a-number")  # type: ignore


def test_number_equal_validate_question_compatibility() -> None:
    # Compatible with NUMERIC question
    qrule = NumberEqualQuestionRule(
        question_id="Qn", answers=[1.0], config=NumberEqualConfig(approximate=False)
    )
    assert qrule.validate_compatibility({"Qn": NumericQuestion()}) == []
    # Incompatible with TEXT question -> should report an error
    errors = qrule.validate_compatibility({"Qn": TextQuestion()})
    assert errors
    assert any("not compatible" in e for e in errors)


def test_number_equal_config_tolerance_customization() -> None:
    # Tight tolerance fails, loose tolerance passes
    tight = NumberEqualRule(answers=[100.0], config=NumberEqualConfig(tolerance=1e-9))
    loose = NumberEqualRule(answers=[100.0], config=NumberEqualConfig(tolerance=1e-3))
    assert tight.process_answer(100.000001).passed is False
    assert loose.process_answer(100.000001).passed is True


def test_number_equal_feedback_lists_all_correct_answers() -> None:
    rule = NumberEqualRule(answers=[1, 2, 3], config=NumberEqualConfig(approximate=False))
    res = rule.process_answer(4)
    assert res.passed is False
    assert "The correct answers are: 1, 2, 3." in res.feedback
