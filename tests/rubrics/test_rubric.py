import pytest

from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models import ChoiceQuestion, TextQuestion
from gradeflow_engine.rubrics.model import Rubric, RubricCoverage
from gradeflow_engine.rules.models.exact_match import ExactMatchQuestionRule
from gradeflow_engine.rules.models.length import LengthQuestionRule
from gradeflow_engine.rules.models.multiple_choice import MultipleChoiceQuestionRule
from gradeflow_engine.submissions.models import Submission


def make_question_set() -> QuestionSet:
    # Two questions: q1 is TEXT, q2 is CHOICE
    q1 = TextQuestion(description="A text question")
    q2 = ChoiceQuestion(description="A choice question")
    return QuestionSet(question_map={"q1": q1, "q2": q2})


def test_length_rule_grading_and_points() -> None:
    # length rule for q1: min 5, max 20, max_points defaults to 1.0
    length_rule = LengthQuestionRule(question_id="q1", min_length=5, max_length=20, max_points=2.0)
    rubric = Rubric(rules=[length_rule])

    # submission with short answer -> fail and 0 points
    submission = Submission(student_id="s1", answer_map={"q1": "hey"})
    graded = rubric.grade([submission])[0]
    assert graded.student_id == "s1"
    assert len(graded.results) == 1
    res = graded.results[0]
    assert res.question_id == "q1"
    assert res.passed is False
    assert res.points == 0.0

    # submission with adequate length -> pass and full points
    submission2 = Submission(student_id="s2", answer_map={"q1": "hello world"})
    graded2 = rubric.grade([submission2])[0]
    res2 = graded2.results[0]
    assert res2.passed is True
    assert res2.points == 2.0


def test_multiple_choice_modes_and_combined_rules() -> None:
    # q2 choices correct are 'a' and 'b'
    mc_all = MultipleChoiceQuestionRule(
        question_id="q2", answer={"a", "b"}, mode="ALL", max_points=3.0
    )
    mc_any = MultipleChoiceQuestionRule(
        question_id="q2", answer={"a", "b"}, mode="ANY", max_points=3.0
    )
    mc_partial = MultipleChoiceQuestionRule(
        question_id="q2", answer={"a", "b"}, mode="PARTIAL", max_points=3.0
    )

    # Use each rule separately to check behaviour
    r_all = Rubric(rules=[mc_all])
    r_any = Rubric(rules=[mc_any])
    r_part = Rubric(rules=[mc_partial])

    sub = Submission(student_id="s1", answer_map={"q2": {"a"}})

    g_all = r_all.grade([sub])[0].results[0]
    assert g_all.passed is False  # ALL requires both a and b

    g_any = r_any.grade([sub])[0].results[0]
    assert g_any.passed is True

    g_part = r_part.grade([sub])[0].results[0]
    # partial with one correct and zero incorrect should give 0.5 of max points
    assert pytest.approx(g_part.points) == 1.5  # type: ignore

    # combine length rule for q1 and multiple choice rule for q2 in same rubric
    length_rule = LengthQuestionRule(question_id="q1", min_length=1, max_length=100, max_points=1.0)
    combined = Rubric(rules=[length_rule, mc_any])
    sub2 = Submission(student_id="s2", answer_map={"q1": "ok", "q2": {"z"}})
    graded = combined.grade([sub2])[0]
    # should produce two results (one per rule)
    assert len(graded.results) == 2


def test_missing_answer_raises_value_error() -> None:
    mc = MultipleChoiceQuestionRule(question_id="q2", answer={"a"}, mode="ALL")
    rubric = Rubric(rules=[mc])
    # submission missing q2
    sub = Submission(student_id="s1", answer_map={})
    with pytest.raises(ValueError):
        rubric.grade([sub])


def test_validate_questions_exist_and_compatibility_and_unique() -> None:
    qs = make_question_set()
    question_map = qs.question_map

    # Rule referencing nonexistent question id
    bad_exist = LengthQuestionRule(question_id="not_a_q", min_length=1)
    rubric1 = Rubric(rules=[bad_exist])
    errors = rubric1.validate_questions_exist(set(question_map.keys()))
    assert any("does not exist" in e for e in errors)

    # Rule incompatible with question type: length rule against choice question q2
    bad_compat = LengthQuestionRule(question_id="q2", min_length=1)
    rubric2 = Rubric(rules=[bad_compat])
    compat_errors = rubric2.validate_compatibility(question_map)
    assert len(compat_errors) == 1

    # Unique target questions: duplicate targeting should produce error
    mc1 = MultipleChoiceQuestionRule(question_id="q2", answer={"a"})
    mc2 = MultipleChoiceQuestionRule(question_id="q2", answer={"b"})
    rubric_dup = Rubric(rules=[mc1, mc2])
    unique_errors = rubric_dup.validate_unique_target_questions()
    assert any("targeted by multiple rules" in e for e in unique_errors)

    # validate_rubric aggregates all checks
    agg_errors = rubric_dup.validate_rubric(qs)
    # should include compatibility (none here for mc against choice), and unique target error
    assert any("targeted by multiple rules" in e for e in agg_errors)


def test_rubric_get_coverage_basic() -> None:
    # QuestionSet has Q1, Q2
    qset = QuestionSet(question_map={"Q1": TextQuestion(), "Q2": TextQuestion()})

    # Rubric targets Q1 (exists) and Q999 (non-existent)
    r1 = ExactMatchQuestionRule(question_id="Q1", answers=["foo"], max_points=1.0)
    r2 = ExactMatchQuestionRule(question_id="Q999", answers=["bar"], max_points=1.0)
    rubric = Rubric(rules=[r1, r2])

    cov: RubricCoverage = rubric.get_coverage(qset)

    assert cov.total == 2
    # Only Q1 should be counted as covered because it's in the question set
    assert cov.covered == 1
    assert cov.percentage == pytest.approx(0.5)  # type: ignore
    assert cov.question_ids == {"Q1", "Q2"}
    assert cov.covered_question_ids == {"Q1"}


def test_rubric_get_coverage_empty_qset() -> None:
    qset = QuestionSet(question_map={})
    r1 = ExactMatchQuestionRule(question_id="Q1", answers=["foo"], max_points=1.0)
    rubric = Rubric(rules=[r1])

    cov = rubric.get_coverage(qset)
    assert cov.total == 0
    assert cov.covered == 0
    assert cov.percentage == 0.0
    assert cov.question_ids == set()
    assert cov.covered_question_ids == set()
