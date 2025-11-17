from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.similarity import (
    SimilarityQuestionRule,
    SimilarityRule,
)


def test_similarity_levenshtein_passes_and_feedback() -> None:
    rule = SimilarityRule(reference="hello world", threshold=0.8, algorithm="levenshtein")
    # close typo should still be above threshold
    result = rule.process_answer("hello worlld")

    assert isinstance(result.output, float)
    assert result.passed is True
    assert "Match" in result.feedback or "Match" in result.feedback
    assert result.rule == "SimilarityRule"


def test_similarity_jaro_winkler_below_threshold() -> None:
    rule = SimilarityRule(reference="goodbye", threshold=0.95, algorithm="jaro_winkler")
    result = rule.process_answer("badbye")

    assert result.passed is False
    assert "Insufficient similarity" in result.feedback


def test_similarity_question_rule_points() -> None:
    qrule = SimilarityQuestionRule(
        question_id="q1",
        reference="yes",
        threshold=0.5,
        algorithm="levenshtein",
        max_points=3.0,
    )
    submission1: dict[QuestionId, Answer] = {"q1": "yes"}
    qresult = qrule.process_submission(submission1)

    assert qresult.question_id == "q1"
    assert qresult.max_points == 3.0
    assert qresult.points == 3.0

    submission2: dict[QuestionId, Answer] = {"q1": "ye"}
    qresult = qrule.process_submission(submission2)

    assert qresult.points == 3.0

    submission3: dict[QuestionId, Answer] = {"q1": "y"}
    qresult = qrule.process_submission(submission3)

    assert qresult.points == 0.0
