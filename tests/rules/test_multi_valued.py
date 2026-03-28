from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models import SingleTargetRule
from gradeflow_engine.rules.models.multi_valued import MultiValuedQuestionRule
from gradeflow_engine.rules.models.text_match import TextMatchRule


def test_multi_valued_all_pass() -> None:
    # All inner rules match -> passed True and full points
    rules: list[SingleTargetRule] = [
        TextMatchRule(answers=["A"]),
        TextMatchRule(answers=["B"]),
    ]
    qrule = MultiValuedQuestionRule(question_id="q", rules=rules, aggregation="ALL")

    submission: dict[QuestionId, Answer] = {"q": ["A", "B"]}
    qresult = qrule.process_submission(submission, {"q": 4.0})["q"]

    assert qresult.points == 4.0
    assert qresult.max_points == 4.0


def test_multi_valued_any_pass() -> None:
    # Only one inner rule matches -> ANY should pass and award full points
    rules: list[SingleTargetRule] = [
        TextMatchRule(answers=["A"]),
        TextMatchRule(answers=["B"]),
    ]
    qrule = MultiValuedQuestionRule(question_id="q", rules=rules, aggregation="ANY")

    submission: dict[QuestionId, Answer] = {"q": ["A", "X"]}
    qresult = qrule.process_submission(submission, {"q": 3.0})["q"]

    assert qresult.points == 3.0
    assert qresult.max_points == 3.0


def test_multi_valued_partial_points() -> None:
    # PARTIAL aggregation returns fractional points
    rules: list[SingleTargetRule] = [
        TextMatchRule(answers=["A"]),
        TextMatchRule(answers=["B"]),
        TextMatchRule(answers=["C"]),
    ]
    qrule = MultiValuedQuestionRule(question_id="q", rules=rules, aggregation="PARTIAL")

    submission: dict[QuestionId, Answer] = {"q": ["A", "X", "C"]}
    qresult = qrule.process_submission(submission, {"q": 6.0})["q"]

    # Two of three matched -> 2/3 of max_points
    assert abs(qresult.points - (6.0 * 2 / 3)) < 1e-6
