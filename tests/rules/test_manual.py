import pytest

from gradeflow_engine.exceptions import MissingAnswerError
from gradeflow_engine.questions.models import ChoiceQuestion, NumericQuestion, TextQuestion
from gradeflow_engine.questions.models.multi_valued import MultiValuedQuestion
from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.manual import ManualQuestionRule, ManualRule


def test_manual_rule_basic_result_properties() -> None:
    rule = ManualRule()
    res = rule.process_answer("anything")

    assert res.output == 0
    assert res.passed is False
    assert res.graded is False
    assert "Manual grading required" in res.feedback
    assert res.rule == "ManualRule"


def test_manual_question_rule_points_zero() -> None:
    qrule = ManualQuestionRule(question_id="Q1")
    submission: dict[QuestionId, Answer] = {"Q1": "some answer"}

    qres = qrule.process_submission(submission, {"Q1": 5.0})["Q1"]
    assert qres.max_points == 5.0
    assert qres.points == 0.0
    # Feedback and graded flag propagated from ManualRule
    assert qres.graded is False
    assert "Manual grading required" in qres.feedback


def test_manual_question_rule_missing_answer_raises() -> None:
    qrule = ManualQuestionRule(question_id="Q_missing")
    with pytest.raises(MissingAnswerError) as exc_info:
        _ = qrule.process_submission({}, {})
    assert exc_info.value.question_id == "Q_missing"


def test_manual_rule_compatibility_all_question_types() -> None:
    # ManualRule declares compatibility with TEXT, NUMERIC, CHOICE, MULTI_VALUED
    txt = TextQuestion()
    num = NumericQuestion()
    ch = ChoiceQuestion()
    mv = MultiValuedQuestion(value_types=["TEXT", "NUMERIC"])

    r = ManualQuestionRule(question_id="Q")

    # validate_compatibility requires a question_map keyed by question_id
    assert r.validate_compatibility({"Q": txt}) == []
    assert r.validate_compatibility({"Q": num}) == []
    assert r.validate_compatibility({"Q": ch}) == []
    assert r.validate_compatibility({"Q": mv}) == []


def test_manual_rule_description() -> None:
    assert "Manual" in ManualRule().description
