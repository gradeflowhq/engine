from typing import Any, cast

import pytest

from gradeflow_engine.exceptions import GradingError
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models import ChoiceQuestion, TextQuestion
from gradeflow_engine.rubrics.model import Rubric, RubricCoverage, grade_submission
from gradeflow_engine.rules.models.conditional import ConditionalMultiQuestionRule
from gradeflow_engine.rules.models.length import LengthQuestionRule
from gradeflow_engine.rules.models.multiple_choice import MultipleChoiceQuestionRule
from gradeflow_engine.rules.models.programmable import ProgrammableMultiQuestionRule
from gradeflow_engine.rules.models.text_match import TextMatchQuestionRule
from gradeflow_engine.rules.result import QuestionResult
from gradeflow_engine.submissions.models import Submission


def make_question_set() -> QuestionSet:
    # Two questions: q1 is TEXT, q2 is CHOICE
    q1 = TextQuestion(description="A text question")
    q2 = ChoiceQuestion(description="A choice question")
    return QuestionSet(question_map={"q1": q1, "q2": q2})


def test_length_rule_grading_and_points() -> None:
    # length rule for q1: min 5, max 20, max_points defaults to 1.0
    length_rule = LengthQuestionRule(question_id="q1", min_length=5, max_length=20)
    rubric = Rubric(rules=[length_rule])
    q1_map = {"q1": TextQuestion(max_points=2.0)}

    # submission with short answer -> fail and 0 points
    submission = Submission(student_id="s1", answer_map={"q1": "hey"})
    graded = rubric.grade([submission], q1_map)[0]
    assert graded.student_id == "s1"
    assert len(graded.result_map) == 1
    res = graded.result_map["q1"]
    assert res.passed is False
    assert res.points == 0.0

    # submission with adequate length -> pass and full points
    submission2 = Submission(student_id="s2", answer_map={"q1": "hello world"})
    graded2 = rubric.grade([submission2], q1_map)[0]
    res2 = graded2.result_map["q1"]
    assert res2.passed is True
    assert res2.points == 2.0


def test_multiple_choice_modes_and_combined_rules() -> None:
    # q2 choices correct are 'a' and 'b'
    mc_all = MultipleChoiceQuestionRule(question_id="q2", answer={"a", "b"}, mode="ALL")
    mc_any = MultipleChoiceQuestionRule(question_id="q2", answer={"a", "b"}, mode="ANY")
    mc_partial = MultipleChoiceQuestionRule(question_id="q2", answer={"a", "b"}, mode="PARTIAL")

    # Use each rule separately to check behaviour
    r_all = Rubric(rules=[mc_all])
    r_any = Rubric(rules=[mc_any])
    r_part = Rubric(rules=[mc_partial])

    sub = Submission(student_id="s1", answer_map={"q2": {"a"}})

    g_all = r_all.grade([sub], {})[0].result_map["q2"]
    assert g_all.passed is False  # ALL requires both a and b

    g_any = r_any.grade([sub], {})[0].result_map["q2"]
    assert g_any.passed is True

    g_part = r_part.grade([sub], {"q2": ChoiceQuestion(max_points=3.0)})[0].result_map["q2"]
    # partial with one correct and zero incorrect should give 0.5 of max points
    assert pytest.approx(g_part.points) == 1.5  # type: ignore

    # combine length rule for q1 and multiple choice rule for q2 in same rubric
    length_rule = LengthQuestionRule(question_id="q1", min_length=1, max_length=100)
    combined = Rubric(rules=[length_rule, mc_any])
    sub2 = Submission(student_id="s2", answer_map={"q1": "ok", "q2": {"z"}})
    graded = combined.grade([sub2], {})[0]
    # should produce two results (one per rule)
    assert len(graded.result_map) == 2


def test_missing_answer_strict_raises_grading_error() -> None:
    from gradeflow_engine.exceptions import GradingError

    mc = MultipleChoiceQuestionRule(question_id="q2", answer={"a"}, mode="ALL")
    rubric = Rubric(rules=[mc])
    # submission missing q2 — non-strict grades silently with 0 points
    sub = Submission(student_id="s1", answer_map={})
    graded = rubric.grade([sub], {})
    assert graded[0].result_map["q2"].points == 0.0
    # strict=True should propagate as GradingError
    with pytest.raises(GradingError) as exc_info:
        rubric.grade([sub], {}, strict=True)
    assert exc_info.value.student_id == "s1"
    assert exc_info.value.question_id == "q2"


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
    r1 = TextMatchQuestionRule(question_id="Q1", answers=["foo"])
    r2 = TextMatchQuestionRule(question_id="Q999", answers=["bar"])
    rubric = Rubric(rules=[r1, r2])

    cov: RubricCoverage = rubric.get_coverage(qset)

    assert cov.total == 2
    # Only Q1 should be counted as covered because it's in the question set
    assert cov.covered == 1
    assert cov.percentage == pytest.approx(0.5)  # type: ignore
    assert cov.question_ids == {"Q1", "Q2"}
    assert cov.covered_question_ids == {"Q1"}
    assert cov.uncovered_question_ids == {"Q2"}
    assert cov.question_rules == {"Q1": r1.id}
    assert cov.global_rules == {}
    assert cov.questions_by_rule == {r1.id: {"Q1"}}


def test_rubric_get_coverage_empty_qset() -> None:
    qset = QuestionSet(question_map={})
    r1 = TextMatchQuestionRule(question_id="Q1", answers=["foo"])
    rubric = Rubric(rules=[r1])

    cov = rubric.get_coverage(qset)
    assert cov.total == 0
    assert cov.covered == 0
    assert cov.percentage == 0.0
    assert cov.question_ids == set()
    assert cov.covered_question_ids == set()
    assert cov.uncovered_question_ids == set()
    assert cov.question_rules == {}
    assert cov.global_rules == {}
    assert cov.questions_by_rule == {}


def test_rubric_get_coverage_returns_rule_maps() -> None:
    qset = QuestionSet(
        question_map={
            "Q1": TextQuestion(),
            "Q2": TextQuestion(),
            "Q3": ChoiceQuestion(),
            "Q4": TextQuestion(),
        }
    )
    direct = TextMatchQuestionRule(id="direct", question_id="Q1", answers=["x"])
    global_rule = ProgrammableMultiQuestionRule(
        id="global",
        target_question_ids=["Q2", "Q3"],
    )
    rubric = Rubric(rules=[direct, global_rule])

    coverage = rubric.get_coverage(qset)

    assert coverage.question_rules == {"Q1": "direct"}
    assert coverage.global_rules == {"Q2": "global", "Q3": "global"}
    assert coverage.questions_by_rule == {
        "direct": {"Q1"},
        "global": {"Q2", "Q3"},
    }
    assert coverage.covered_question_ids == {"Q1", "Q2", "Q3"}
    assert coverage.uncovered_question_ids == {"Q4"}
    assert direct.scope == "question"
    assert global_rule.scope == "global"


def test_serialization_schemas_require_backend_guaranteed_fields() -> None:
    coverage_schema = RubricCoverage.model_json_schema(mode="serialization")
    assert set(coverage_schema["required"]) >= {
        "question_ids",
        "covered_question_ids",
        "uncovered_question_ids",
        "question_rules",
        "global_rules",
        "questions_by_rule",
        "total",
        "covered",
        "percentage",
    }

    output_schema = TextMatchQuestionRule.model_json_schema(mode="serialization")
    assert set(output_schema["required"]) >= {
        "id",
        "question_types",
        "constraints",
        "scope",
        "question_id",
        "type",
        "display_name",
        "answers",
        "description",
    }

    input_schema = TextMatchQuestionRule.model_json_schema(mode="validation")
    assert set(input_schema["required"]) == {"question_id", "answers"}


def test_rubric_stale_rule_references_and_pruning_are_top_level() -> None:
    qset = make_question_set()
    keep = TextMatchQuestionRule(id="keep", question_id="q1", answers=["x"])
    stale = ConditionalMultiQuestionRule(
        id="stale",
        if_rules=[TextMatchQuestionRule(question_id="missing-if", answers=["x"])],
        then_rules=[TextMatchQuestionRule(question_id="q1", answers=["x"])],
        else_rules=[TextMatchQuestionRule(question_id="missing-else", answers=["x"])],
    )
    rubric = Rubric(rules=[keep, stale])

    references = rubric.get_stale_rule_references(qset)
    pruned = rubric.remove_stale_rules(qset)

    assert [(ref.rule_id, ref.qids) for ref in references] == [
        ("stale", ["missing-else", "missing-if"]),
    ]
    assert [rule.id for rule in pruned.rules] == ["keep"]


def test_rubric_no_rules_no_answer() -> None:
    qset = QuestionSet(
        question_map={"Q1": TextQuestion(max_points=10.0), "Q2": ChoiceQuestion(max_points=5.0)}
    )
    rubric = Rubric(rules=[TextMatchQuestionRule(question_id="Q1", answers=["foo"])])
    cov = rubric.get_coverage(qset)
    assert cov.total == 2
    assert cov.covered == 1
    assert cov.percentage == 0.5

    sub = Submission(student_id="s1", answer_map={"Q1": "foo"})

    # Grade with grade_questions_without_rule=False
    graded = rubric.grade(
        [sub],
        qset.question_map,
        strict=False,
        override_results=True,
        grade_questions_without_rule=False,
    )[0]

    # Grading should be processed for Q1 but not Q2 (which has no rules)
    assert graded.student_id == "s1"
    assert "Q1" in graded.result_map
    assert graded.result_map["Q1"].points == 10.0
    assert graded.result_map["Q1"].max_points == 10.0
    assert graded.result_map["Q1"].passed is True
    assert graded.result_map["Q1"].rule == "Text Match"

    # Q2 should not be graded since it's not covered by any rule
    assert "Q2" not in graded.result_map

    # Grade with grade_questions_without_rule=True
    graded = rubric.grade(
        [sub],
        qset.question_map,
        strict=False,
        override_results=True,
        grade_questions_without_rule=True,
    )[0]

    # Grading should be processed for Q1
    assert graded.student_id == "s1"
    assert "Q1" in graded.result_map
    assert graded.result_map["Q1"].points == 10.0
    assert graded.result_map["Q1"].max_points == 10.0
    assert graded.result_map["Q1"].passed is True
    assert graded.result_map["Q1"].rule == "Text Match"

    # Grading should be processed for Q1
    assert "Q2" in graded.result_map
    assert graded.result_map["Q2"].points == 0.0
    assert graded.result_map["Q2"].max_points == 5.0
    assert graded.result_map["Q2"].passed is False
    assert graded.result_map["Q2"].rule == "No Rule"


def test_rubric_grading_exception_and_partial_override_paths() -> None:
    class BadRule:
        type = "BAD"

        def get_target_question_ids(self) -> set[str]:
            return {"Q1"}

        def process_submission(
            self, answer_map: dict[str, object], max_points_map: dict[str, float]
        ) -> dict[str, QuestionResult]:
            raise RuntimeError("bad rule")

    class TwoResultRule:
        type = "TWO"

        def get_target_question_ids(self) -> set[str]:
            return {"Q1", "Q2"}

        def process_submission(
            self, answer_map: dict[str, object], max_points_map: dict[str, float]
        ) -> dict[str, QuestionResult]:
            return {
                qid: QuestionResult(
                    output=True,
                    passed=True,
                    feedback="",
                    rule="TWO",
                    points=1,
                    max_points=1,
                )
                for qid in self.get_target_question_ids()
            }

    submission = Submission(student_id="s1", answer_map={"Q1": "x", "Q2": "y"})
    question_map = {"Q1": TextQuestion(), "Q2": TextQuestion()}

    with pytest.raises(GradingError):
        grade_submission([cast(Any, BadRule())], submission, question_map, strict=True)

    graded = grade_submission([cast(Any, BadRule())], submission, question_map, strict=False)
    fallback = graded.result_map["Q1"]
    assert fallback.rule == "Manual"
    assert fallback.feedback == "Manual grading required."
    assert fallback.graded is False
    assert fallback.points == 0.0
    assert fallback.max_points == 1.0

    existing = QuestionResult(
        output=True,
        passed=True,
        feedback="existing",
        rule="Existing",
        points=9,
        max_points=9,
    )
    submission = submission.model_copy(update={"result_map": {"Q1": existing}})
    graded = grade_submission(
        [cast(Any, TwoResultRule())],
        submission,
        question_map,
        override_results=False,
        grade_questions_without_rule=False,
    )
    assert graded.result_map["Q1"] is existing
    assert graded.result_map["Q2"].rule == "TWO"

    submission = submission.model_copy(update={"result_map": {"Q1": existing, "Q2": existing}})
    skipped = grade_submission(
        [cast(Any, TwoResultRule())],
        submission,
        question_map,
        override_results=False,
        grade_questions_without_rule=False,
    )
    assert skipped.result_map == submission.result_map
