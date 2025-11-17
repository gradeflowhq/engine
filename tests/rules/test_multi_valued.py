from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models import SingleTargetRule
from gradeflow_engine.rules.models.exact_match import ExactMatchRule
from gradeflow_engine.rules.models.multi_valued import MultiValuedQuestionRule


def test_multi_valued_all_pass() -> None:
    # All inner rules match -> passed True and full points
    rules: list[SingleTargetRule] = [
        ExactMatchRule(answer="A"),
        ExactMatchRule(answer="B"),
    ]
    qrule = MultiValuedQuestionRule(question_id="q", rules=rules, aggregation="ALL", max_points=4.0)

    submission: dict[QuestionId, Answer] = {"q": ["A", "B"]}
    qresult = qrule.process_submission(submission)

    assert qresult.points == 4.0
    assert qresult.max_points == 4.0
    assert qresult.question_id == "q"


def test_multi_valued_any_pass() -> None:
    # Only one inner rule matches -> ANY should pass and award full points
    rules: list[SingleTargetRule] = [
        ExactMatchRule(answer="A"),
        ExactMatchRule(answer="B"),
    ]
    qrule = MultiValuedQuestionRule(question_id="q", rules=rules, aggregation="ANY", max_points=3.0)

    submission: dict[QuestionId, Answer] = {"q": ["A", "X"]}
    qresult = qrule.process_submission(submission)

    assert qresult.points == 3.0
    assert qresult.max_points == 3.0


def test_multi_valued_partial_points() -> None:
    # PARTIAL aggregation returns fractional points
    rules: list[SingleTargetRule] = [
        ExactMatchRule(answer="A"),
        ExactMatchRule(answer="B"),
        ExactMatchRule(answer="C"),
    ]
    qrule = MultiValuedQuestionRule(
        question_id="q", rules=rules, aggregation="PARTIAL", max_points=6.0
    )

    submission: dict[QuestionId, Answer] = {"q": ["A", "X", "C"]}
    qresult = qrule.process_submission(submission)

    # Two of three matched -> 2/3 of max_points
    assert abs(qresult.points - (6.0 * 2 / 3)) < 1e-6
