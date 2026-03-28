from gradeflow_engine.questions.models import ChoiceQuestion, NumericQuestion, TextQuestion
from gradeflow_engine.questions.models.multi_valued import MultiValuedQuestion
from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.bonus import BonusQuestionRule, BonusRule


def test_bonus_rule_basic_result_properties() -> None:
    rule = BonusRule()
    res = rule.process_answer("anything")

    assert res.output == 1
    assert res.passed is True
    assert res.graded is True
    assert "Bonus points awarded" in res.feedback
    assert res.rule == "BonusRule"


def test_bonus_question_rule_awards_full_points() -> None:
    qrule = BonusQuestionRule(question_id="Q1")
    submission: dict[QuestionId, Answer] = {"Q1": "ignored"}

    qres = qrule.process_submission(submission, {"Q1": 3.5})["Q1"]
    assert qres.max_points == 3.5
    assert qres.points == 3.5
    assert qres.passed is True
    assert "Bonus points awarded" in qres.feedback


def test_bonus_question_rule_missing_answer_raises() -> None:
    qrule = BonusQuestionRule(question_id="Q_missing")
    try:
        _ = qrule.process_submission({}, {})
        raise AssertionError("Expected ValueError for missing answer")
    except ValueError:
        pass


def test_bonus_rule_compatibility_all_question_types() -> None:
    # BonusRule declares compatibility with TEXT, NUMERIC, CHOICE, MULTI_VALUED
    txt = TextQuestion()
    num = NumericQuestion()
    ch = ChoiceQuestion()
    mv = MultiValuedQuestion(value_types=["TEXT", "NUMERIC"])

    r = BonusQuestionRule(question_id="Q")

    # validate_compatibility requires a question_map keyed by question_id
    assert r.validate_compatibility({"Q": txt}) == []
    assert r.validate_compatibility({"Q": num}) == []
    assert r.validate_compatibility({"Q": ch}) == []
    assert r.validate_compatibility({"Q": mv}) == []
