import logging
from collections.abc import Mapping, Sequence
from typing import Literal, TypeAlias

from joblib import Parallel, delayed, effective_n_jobs
from pydantic import BaseModel, ConfigDict

from ..exceptions import GradingError, MissingAnswerError
from ..question_sets.model import QuestionSet
from ..questions.models import Question
from ..questions.types import QuestionId
from ..rules.models import QuestionRule
from ..rules.models.base import DEFAULT_MAX_POINTS
from ..rules.result import QuestionResult
from ..rules.types import RuleId, RuleValidationError
from ..rules.validators import validate_unique_target_questions_in_rules
from ..submissions.models import Submission

RubricGradingParallelMode: TypeAlias = Literal["processes", "threads"]


def _missing_answer_result(max_points: float) -> QuestionResult:
    return QuestionResult(
        points=0.0,
        max_points=max_points,
        feedback="No answer provided.",
        rule="No Answer",
        passed=False,
        output=0.0,
    )


def _zero_point_result(max_points: float) -> QuestionResult:
    """Result assigned to questions that have no rule and no existing result."""
    return QuestionResult(
        points=0.0,
        max_points=max_points,
        feedback="",
        rule="No Rule",
        passed=False,
        output=0.0,
    )


def _ungraded_result(max_points: float) -> QuestionResult:
    return QuestionResult(
        points=0.0,
        max_points=max_points,
        feedback="Manual grading required.",
        rule="Manual",
        passed=False,
        output=0.0,
        graded=False,
    )


def _handle_missing_answer(
    e: MissingAnswerError,
    submission: Submission,
    rule: QuestionRule,
    max_points_map: dict[QuestionId, float],
    strict: bool,
) -> dict[QuestionId, QuestionResult]:
    if strict:
        raise GradingError(
            student_id=submission.student_id,
            question_id=e.question_id,
            reason=(f"Missing answer for question ID {e.question_id} required by rule {rule.type}"),
        ) from e
    logging.warning(
        f"Missing answer for question ID {e.question_id} required by rule {rule.type} "
        f"in submission from student {submission.student_id}. "
        f"Assigning 0 points for this question."
    )
    result = {
        question_id: _missing_answer_result(
            max_points=max_points_map.get(question_id, DEFAULT_MAX_POINTS)
        )
        for question_id in rule.get_target_question_ids()
    }
    return result


def _handle_grading_exception(
    e: Exception,
    submission: Submission,
    rule: QuestionRule,
    max_points_map: dict[QuestionId, float],
    strict: bool,
) -> dict[QuestionId, QuestionResult]:
    if strict:
        raise GradingError(
            student_id=submission.student_id,
            question_id=", ".join(sorted(rule.get_target_question_ids())),
            reason=str(e),
        ) from e
    logging.error(
        f"Error processing rule {rule.type} for submission from student "
        f"{submission.student_id}: {e}. "
        f"Assigning 0 points for affected questions."
    )
    result = {
        question_id: _ungraded_result(max_points=max_points_map.get(question_id, 0.0))
        for question_id in rule.get_target_question_ids()
    }
    return result


def grade_submission(
    rules: Sequence[QuestionRule],
    submission: Submission,
    question_map: Mapping[QuestionId, Question],
    strict: bool = False,
    override_results: bool = True,
    grade_questions_without_rule: bool = True,
) -> Submission:
    """
    Grade a single submission against a list of rules.

    Parameters
    ----------
    strict:
        When True, any error during grading (e.g. missing answer, exception in rule processing)
        raises a GradingError that propagates out of this function.
        When False (default), grading errors are caught and logged, and the affected question(s)
        receive a zero-point result
    override_results:
        When True (default), a rule result **overwrites** any pre-existing
        result for the targeted question(s).  When False, a rule is **skipped**
        for any question that already has a result in the submission's
        ``result_map`` (e.g. pre-populated pass-through points from the CSV
        adapter).
    grade_questions_without_rule:
        When True (default), every question in ``question_map`` that is **not**
        targeted by any rule and has **no** existing result receives a
        zero-point ``QuestionResult`` with ``rule="No Rule"``.  When False,
        uncovered questions are left out of ``result_map`` entirely.
    """
    max_points_map: dict[QuestionId, float] = {qid: q.max_points for qid, q in question_map.items()}
    result_map: dict[QuestionId, QuestionResult] = dict(submission.result_map)

    # Track every question ID that at least one rule targets.
    covered_qids: set[QuestionId] = set()

    for rule in rules:
        target_qids = rule.get_target_question_ids()
        covered_qids.update(target_qids)

        # override_results=False: skip rule if ALL targets already have results.
        if not override_results and all(qid in result_map for qid in target_qids):
            continue

        try:
            new_results = rule.process_submission(submission.answer_map, max_points_map)
        except MissingAnswerError as e:
            new_results = _handle_missing_answer(e, submission, rule, max_points_map, strict)
        except Exception as e:
            new_results = _handle_grading_exception(e, submission, rule, max_points_map, strict)

        if override_results:
            result_map.update(new_results)
        else:
            # Only write results for questions that do NOT yet have a result.
            for qid, qresult in new_results.items():
                if qid not in result_map:
                    result_map[qid] = qresult

    # grade_questions_without_rule: zero-fill uncovered questions.
    if grade_questions_without_rule:
        for qid, question in question_map.items():
            if qid not in covered_qids and qid not in result_map:
                result_map[qid] = _zero_point_result(max_points=question.max_points)

    return submission.model_copy(update={"result_map": result_map})


def _submission_chunks(
    submissions: Sequence[Submission], chunk_count: int
) -> list[Sequence[Submission]]:
    chunk_size = max(1, (len(submissions) + chunk_count - 1) // chunk_count)
    return [
        submissions[index : index + chunk_size] for index in range(0, len(submissions), chunk_size)
    ]


def _grade_submissions(
    rules: Sequence[QuestionRule],
    submissions: Sequence[Submission],
    question_map: Mapping[QuestionId, Question],
    strict: bool,
    override_results: bool,
    grade_questions_without_rule: bool,
) -> list[Submission]:
    return [
        grade_submission(
            rules,
            submission,
            question_map,
            strict=strict,
            override_results=override_results,
            grade_questions_without_rule=grade_questions_without_rule,
        )
        for submission in submissions
    ]


def _grade_parallel_submissions(
    rules: Sequence[QuestionRule],
    submissions: Sequence[Submission],
    question_map: Mapping[QuestionId, Question],
    strict: bool,
    override_results: bool,
    grade_questions_without_rule: bool,
    parallel_jobs: int,
    parallel_mode: RubricGradingParallelMode,
) -> list[Submission]:
    worker_count = min(len(submissions), effective_n_jobs(parallel_jobs))
    chunks = _submission_chunks(submissions, worker_count)
    graded_chunks = Parallel(n_jobs=worker_count, prefer=parallel_mode)(
        delayed(_grade_submissions)(
            rules,
            chunk,
            question_map,
            strict,
            override_results,
            grade_questions_without_rule,
        )
        for chunk in chunks
    )
    return [submission for chunk in graded_chunks for submission in chunk]


class RubricCoverage(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    question_ids: set[QuestionId]
    covered_question_ids: set[QuestionId]
    uncovered_question_ids: set[QuestionId]

    question_rules: dict[QuestionId, RuleId]
    global_rules: dict[QuestionId, RuleId]
    questions_by_rule: dict[RuleId, set[QuestionId]]

    total: int
    covered: int
    percentage: float


class StaleRuleReference(BaseModel):
    rule_id: RuleId
    qids: list[QuestionId]


class Rubric(BaseModel):
    rules: list[QuestionRule]

    def grade(
        self,
        submissions: list[Submission],
        question_map: Mapping[QuestionId, Question],
        strict: bool = False,
        override_results: bool = True,
        grade_questions_without_rule: bool = True,
        parallel_jobs: int = 1,
        parallel_mode: RubricGradingParallelMode = "processes",
    ) -> list[Submission]:
        if parallel_jobs == 0:
            raise ValueError("parallel_jobs must not be 0")
        if parallel_jobs == 1 or len(submissions) <= 1:
            return _grade_submissions(
                self.rules,
                submissions,
                question_map,
                strict,
                override_results,
                grade_questions_without_rule,
            )
        return _grade_parallel_submissions(
            self.rules,
            submissions,
            question_map,
            strict,
            override_results,
            grade_questions_without_rule,
            parallel_jobs,
            parallel_mode,
        )

    def validate_questions_exist(self, question_ids: set[QuestionId]) -> list[RuleValidationError]:
        return [
            error for rule in self.rules for error in rule.validate_questions_exist(question_ids)
        ]

    def validate_compatibility(
        self, question_map: dict[QuestionId, Question]
    ) -> list[RuleValidationError]:
        return [error for rule in self.rules for error in rule.validate_compatibility(question_map)]

    def validate_unique_target_questions(self) -> list[RuleValidationError]:
        return validate_unique_target_questions_in_rules(self.rules)

    def validate_rubric(self, question_set: QuestionSet) -> list[RuleValidationError]:
        question_map = question_set.question_map
        question_ids = set(question_map.keys())
        errors = (
            self.validate_questions_exist(question_ids)
            + self.validate_compatibility(question_map)
            + self.validate_unique_target_questions()
        )
        return errors

    def get_target_question_ids(self) -> set[QuestionId]:
        return {
            question_id for rule in self.rules for question_id in rule.get_target_question_ids()
        }

    def get_referenced_question_ids(self) -> set[QuestionId]:
        return {
            question_id for rule in self.rules for question_id in rule.get_referenced_question_ids()
        }

    def get_coverage(self, question_set: QuestionSet) -> RubricCoverage:
        question_ids = set(question_set.question_map.keys())
        question_rules: dict[QuestionId, RuleId] = {}
        global_rules: dict[QuestionId, RuleId] = {}

        for rule in self.rules:
            for qid in rule.get_target_question_ids().intersection(question_ids):
                if rule.scope == "question":
                    question_rules[qid] = rule.id
                elif rule.scope == "global":
                    global_rules[qid] = rule.id

        covered_question_ids = set(question_rules) | set(global_rules)
        uncovered_question_ids = question_ids - covered_question_ids
        questions_by_rule: dict[RuleId, set[QuestionId]] = {}
        for rule_map in (question_rules, global_rules):
            for qid, rule_id in rule_map.items():
                questions_by_rule.setdefault(rule_id, set()).add(qid)

        return RubricCoverage(
            question_ids=question_ids,
            covered_question_ids=covered_question_ids,
            uncovered_question_ids=uncovered_question_ids,
            question_rules=question_rules,
            global_rules=global_rules,
            questions_by_rule=questions_by_rule,
            total=len(question_ids),
            covered=len(covered_question_ids),
            percentage=len(covered_question_ids) / len(question_ids) if question_ids else 0.0,
        )

    def get_stale_rule_references(self, question_set: QuestionSet) -> list[StaleRuleReference]:
        question_ids = set(question_set.question_map.keys())
        references: list[StaleRuleReference] = []
        for rule in self.rules:
            qids = sorted(rule.get_referenced_question_ids() - question_ids)
            if qids:
                references.append(StaleRuleReference(rule_id=rule.id, qids=qids))
        return references

    def remove_stale_rules(self, question_set: QuestionSet) -> "Rubric":
        question_ids = set(question_set.question_map.keys())
        return Rubric(
            rules=[
                rule
                for rule in self.rules
                if rule.get_referenced_question_ids().issubset(question_ids)
            ]
        )
