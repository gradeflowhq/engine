import pytest

from gradeflow_engine.questions.types import Answer, QuestionId
from gradeflow_engine.rules.models.similarity import (
    SimilarityQuestionRule,
    SimilarityRule,
)


def test_similarity_levenshtein_passes_and_feedback() -> None:
    rule = SimilarityRule(
        references=["hello world", "hello code"], threshold=0.8, algorithm="levenshtein"
    )
    # close typo should still be above threshold
    result = rule.process_answer("hello worlld")

    assert isinstance(result.output, float)
    assert result.passed is True
    assert "Match" in result.feedback
    assert "hello world" in result.feedback
    assert "hello code" not in result.feedback
    assert result.rule == "SimilarityRule"


def test_similarity_levenshtein_fails_and_feedback() -> None:
    rule = SimilarityRule(references=["hello world"], threshold=0.8, algorithm="levenshtein")
    result = rule.process_answer("goodbye")

    assert isinstance(result.output, float)
    assert result.passed is False
    assert "Insufficient similarity" in result.feedback
    assert "hello world" in result.feedback
    assert result.rule == "SimilarityRule"


def test_similarity_jaro_winkler_below_threshold() -> None:
    rule = SimilarityRule(references=["goodbye"], threshold=0.95, algorithm="jaro_winkler")
    result = rule.process_answer("badbye")

    assert result.passed is False
    assert "Insufficient similarity" in result.feedback


def test_similarity_jaro_winkler_passes() -> None:
    rule = SimilarityRule(references=["goodbye"], threshold=0.8, algorithm="jaro_winkler")
    result = rule.process_answer("goodbye")

    assert result.passed is True
    assert "Match" in result.feedback


def test_similarity_picks_closest_reference() -> None:
    rule = SimilarityRule(
        references=["apple pie", "banana split"], threshold=0.0, algorithm="levenshtein"
    )
    result = rule.process_answer("apple pye")

    # "apple pye" is closer to "apple pie" than "banana split"
    assert "apple pie" in result.feedback
    assert "banana split" not in result.feedback


def test_similarity_exact_match_passes() -> None:
    rule = SimilarityRule(references=["exact"], threshold=1.0, algorithm="levenshtein")
    result = rule.process_answer("exact")

    assert result.passed is True
    assert result.output == 1.0


def test_similarity_threshold_boundary() -> None:
    rule = SimilarityRule(references=["yes"], threshold=0.5, algorithm="levenshtein")

    # "ye" vs "yes": 2 chars match out of max 3 → normalized similarity = 2/3 ≈ 0.667 → passes
    result_above = rule.process_answer("ye")
    assert result_above.passed is True

    # "y" vs "yes": normalized similarity = 1/3 ≈ 0.333 → fails
    result_below = rule.process_answer("y")
    assert result_below.passed is False


def test_similarity_question_rule_points() -> None:
    qrule = SimilarityQuestionRule(
        question_id="q1",
        references=["yes"],
        threshold=0.5,
        algorithm="levenshtein",
    )
    submission1: dict[QuestionId, Answer] = {"q1": "yes"}
    qresult = qrule.process_submission(submission1, {"q1": 3.0})["q1"]

    assert qresult.max_points == 3.0
    assert qresult.points == 3.0

    submission2: dict[QuestionId, Answer] = {"q1": "ye"}
    qresult = qrule.process_submission(submission2, {"q1": 3.0})["q1"]

    assert qresult.points == 3.0

    submission3: dict[QuestionId, Answer] = {"q1": "y"}
    qresult = qrule.process_submission(submission3, {"q1": 3.0})["q1"]

    assert qresult.points == 0.0


def test_similarity_question_rule_max_points_respected() -> None:
    qrule = SimilarityQuestionRule(
        question_id="q1",
        references=["correct"],
        threshold=0.9,
        algorithm="levenshtein",
    )
    submission: dict[QuestionId, Answer] = {"q1": "correct"}
    qresult = qrule.process_submission(submission, {"q1": 10.0})["q1"]

    assert qresult.max_points == 10.0
    assert qresult.points == 10.0


def test_similarity_description() -> None:
    rule = SimilarityRule(references=["foo", "bar"], threshold=0.75, algorithm="jaro_winkler")
    assert "`foo`" in rule.description
    assert "`bar`" in rule.description
    assert "75%" in rule.description
    assert "Jaro Winkler" in rule.description


# --- transformer ---
# Marked with a custom marker so they can be excluded in environments without the ml extra:
# pytest -m "not ml"


@pytest.mark.ml
def test_similarity_transformer_passes() -> None:
    pytest.importorskip("fastembed", reason="ml extra not installed")

    rule = SimilarityRule(
        references=["the cat sat on the mat"], threshold=0.7, algorithm="transformer"
    )
    result = rule.process_answer("a cat is sitting on a mat")

    assert isinstance(result.output, float)
    assert 0.0 <= result.output <= 1.0
    assert result.passed is True
    assert "Match" in result.feedback
    assert result.rule == "SimilarityRule"


@pytest.mark.ml
def test_similarity_transformer_fails() -> None:
    pytest.importorskip("fastembed", reason="ml extra not installed")

    rule = SimilarityRule(
        references=["the cat sat on the mat"], threshold=0.99, algorithm="transformer"
    )
    result = rule.process_answer("a cat is sitting on a mat")

    assert result.passed is False
    assert "Insufficient similarity" in result.feedback


@pytest.mark.ml
def test_similarity_transformer_picks_closest_reference() -> None:
    pytest.importorskip("fastembed", reason="ml extra not installed")

    rule = SimilarityRule(
        references=["the weather is sunny today", "machine learning is fascinating"],
        threshold=0.0,
        algorithm="transformer",
    )
    result = rule.process_answer("deep learning and AI are interesting")

    assert "machine learning is fascinating" in result.feedback
    assert "the weather is sunny today" not in result.feedback


@pytest.mark.ml
def test_similarity_transformer_output_is_float_in_range() -> None:
    pytest.importorskip("fastembed", reason="ml extra not installed")

    rule = SimilarityRule(references=["hello world"], threshold=0.0, algorithm="transformer")
    result = rule.process_answer("hello world")

    assert isinstance(result.output, float)
    assert result.output >= 0.0
    assert result.output == pytest.approx(1.0, abs=1e-6)


@pytest.mark.ml
def test_similarity_transformer_model_is_cached() -> None:
    pytest.importorskip("fastembed", reason="ml extra not installed")

    from gradeflow_engine.rules.models.similarity import _get_transformer_model

    model_a = _get_transformer_model()
    model_b = _get_transformer_model()

    assert model_a is model_b


@pytest.mark.ml
def test_similarity_transformer_question_rule_points() -> None:
    pytest.importorskip("fastembed", reason="ml extra not installed")

    qrule = SimilarityQuestionRule(
        question_id="q1",
        references=["photosynthesis converts sunlight into energy"],
        threshold=0.7,
        algorithm="transformer",
    )

    submission_pass: dict[QuestionId, Answer] = {
        "q1": "plants use sunlight to produce energy through photosynthesis"
    }
    result_pass = qrule.process_submission(submission_pass, {"q1": 5.0})["q1"]
    assert result_pass.points == 5.0

    submission_fail: dict[QuestionId, Answer] = {"q1": "the moon orbits the earth"}
    result_fail = qrule.process_submission(submission_fail, {"q1": 5.0})["q1"]
    assert result_fail.points == 0.0
