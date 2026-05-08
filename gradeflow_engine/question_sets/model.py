from pydantic import BaseModel, Field

from ..exceptions import AnswerParseError, UnknownQuestionError
from ..questions.constants import UNPARSABLE_MARKER
from ..questions.models import Question
from ..questions.models.choice import ChoiceQuestion
from ..questions.types import Answer, QuestionId
from ..submissions.models import RawSubmission, Submission
from .inference import (
    DEFAULT_CHOICE_DELIMITER,
    DEFAULT_CHOICE_NORMALIZE_CASE,
    DEFAULT_CHOICE_OPTION_LIMIT,
    DEFAULT_EMPTY_MARKER,
    DEFAULT_MULTI_VALUE_DELIMITER,
    get_question_ids,
    get_raw_answers_for_qid,
    infer_question_map,
)


class ChoiceOptionDrift(BaseModel):
    question_id: QuestionId
    missing_options: list[str] = Field(default_factory=list)


class QuestionSetDrift(BaseModel):
    missing_question_ids: list[QuestionId] = Field(default_factory=list)
    extra_question_ids: list[QuestionId] = Field(default_factory=list)
    choice_option_drifts: list[ChoiceOptionDrift] = Field(default_factory=list)
    has_drift: bool = False


def _sorted_values(values: set[str]) -> list[str]:
    return sorted(values, key=lambda value: value.lower())


def _observed_choice_options(question: ChoiceQuestion, raw_answers: list[str]) -> set[str]:
    options: set[str] = set()
    for raw_answer in raw_answers:
        if not raw_answer:
            continue
        answer = {option for option in question.parse(raw_answer) if option}
        options.update(answer)
    return options


def _choice_option_drift(
    question_id: QuestionId,
    question: ChoiceQuestion,
    raw_answers: list[str],
) -> ChoiceOptionDrift | None:
    missing_options = _sorted_values(
        _observed_choice_options(question, raw_answers) - question.options
    )
    if not missing_options:
        return None
    return ChoiceOptionDrift(
        question_id=question_id,
        missing_options=missing_options,
    )


def _sync_choice_question(question: ChoiceQuestion, raw_answers: list[str]) -> ChoiceQuestion:
    observed_options = _observed_choice_options(question, raw_answers)
    return question.model_copy(
        update={
            "options": question.options | observed_options,
        }
    )


def _raw_submissions_for_question_ids(
    raw_submissions: list[RawSubmission], question_ids: set[QuestionId]
) -> list[RawSubmission]:
    return [
        raw_submission.model_copy(
            update={
                "raw_answer_map": {
                    question_id: raw_answer
                    for question_id, raw_answer in raw_submission.raw_answer_map.items()
                    if question_id in question_ids
                }
            }
        )
        for raw_submission in raw_submissions
    ]


class QuestionSet(BaseModel):
    question_map: dict[QuestionId, Question]

    def _parse_raw_answer_map(
        self,
        raw_answer_map: dict[QuestionId, str],
        *,
        strict: bool = False,
    ) -> dict[QuestionId, Answer]:
        answer_map: dict[QuestionId, Answer] = {}
        for qid, raw_answer in raw_answer_map.items():
            question = self.question_map.get(qid)
            if question is None:
                if strict:
                    raise UnknownQuestionError(qid)
                answer_map[qid] = f"{UNPARSABLE_MARKER}{raw_answer}"
                continue
            answer: Answer
            try:
                answer = question.parse(raw_answer)
            except ValueError as e:
                if strict:
                    raise AnswerParseError(qid, raw_answer, str(e)) from e
                answer = f"{UNPARSABLE_MARKER}{raw_answer}"
            answer_map[qid] = answer
        return answer_map

    def _parse_raw_submission(
        self, raw_submission: RawSubmission, *, strict: bool = False
    ) -> Submission:
        answer_map = self._parse_raw_answer_map(raw_submission.raw_answer_map, strict=strict)
        # Fix max_points for any pre-populated result_map entries.
        result_map = {
            qid: (
                result.model_copy(update={"max_points": self.question_map[qid].max_points})
                if qid in self.question_map
                else result
            )
            for qid, result in raw_submission.result_map.items()
        }
        return Submission(
            student_id=raw_submission.student_id,
            answer_map=answer_map,
            result_map=result_map,
        )

    def parse(self, raw_submissions: list[RawSubmission], strict: bool = False) -> list[Submission]:
        return [
            self._parse_raw_submission(raw_submission, strict=strict)
            for raw_submission in raw_submissions
        ]

    def get_drift(self, raw_submissions: list[RawSubmission]) -> QuestionSetDrift:
        submission_question_ids = get_question_ids(raw_submissions)
        question_ids = set(self.question_map)
        choice_option_drifts: list[ChoiceOptionDrift] = []

        for question_id in sorted(question_ids & submission_question_ids):
            question = self.question_map[question_id]
            if not isinstance(question, ChoiceQuestion):
                continue
            option_drift = _choice_option_drift(
                question_id,
                question,
                get_raw_answers_for_qid(raw_submissions, question_id),
            )
            if option_drift is not None:
                choice_option_drifts.append(option_drift)

        missing_question_ids = sorted(submission_question_ids - question_ids)
        extra_question_ids = sorted(question_ids - submission_question_ids)
        return QuestionSetDrift(
            missing_question_ids=missing_question_ids,
            extra_question_ids=extra_question_ids,
            choice_option_drifts=choice_option_drifts,
            has_drift=bool(missing_question_ids or extra_question_ids or choice_option_drifts),
        )

    def sync_from_submissions(
        self,
        raw_submissions: list[RawSubmission],
        *,
        choice_delimiter: str = DEFAULT_CHOICE_DELIMITER,
        choice_option_limit: int = DEFAULT_CHOICE_OPTION_LIMIT,
        choice_normalize_case: bool = DEFAULT_CHOICE_NORMALIZE_CASE,
        multi_value_delimiter: str = DEFAULT_MULTI_VALUE_DELIMITER,
        empty_marker: str = DEFAULT_EMPTY_MARKER,
    ) -> "QuestionSet":
        submission_question_ids = get_question_ids(raw_submissions)
        current_question_ids = set(self.question_map)
        missing_question_ids = submission_question_ids - current_question_ids
        inferred_question_map = (
            type(self)
            .infer(
                _raw_submissions_for_question_ids(raw_submissions, missing_question_ids),
                choice_delimiter=choice_delimiter,
                choice_option_limit=choice_option_limit,
                choice_normalize_case=choice_normalize_case,
                multi_value_delimiter=multi_value_delimiter,
                empty_marker=empty_marker,
            )
            .question_map
            if missing_question_ids
            else {}
        )
        question_map: dict[QuestionId, Question] = {}
        for question_id in sorted(submission_question_ids):
            current_question = self.question_map.get(question_id)
            if current_question is None:
                question_map[question_id] = inferred_question_map[question_id]
            elif isinstance(current_question, ChoiceQuestion):
                question_map[question_id] = _sync_choice_question(
                    current_question,
                    get_raw_answers_for_qid(raw_submissions, question_id),
                )
            else:
                question_map[question_id] = current_question
        return type(self)(question_map=question_map)

    @classmethod
    def infer(
        cls,
        raw_submissions: list[RawSubmission],
        *,
        choice_delimiter: str = DEFAULT_CHOICE_DELIMITER,
        choice_option_limit: int = DEFAULT_CHOICE_OPTION_LIMIT,
        choice_normalize_case: bool = DEFAULT_CHOICE_NORMALIZE_CASE,
        multi_value_delimiter: str = DEFAULT_MULTI_VALUE_DELIMITER,
        empty_marker: str = DEFAULT_EMPTY_MARKER,
    ) -> "QuestionSet":
        if not raw_submissions:
            return cls(question_map={})
        question_map = infer_question_map(
            raw_submissions,
            choice_delimiter=choice_delimiter,
            choice_option_limit=choice_option_limit,
            choice_normalize_case=choice_normalize_case,
            multi_value_delimiter=multi_value_delimiter,
            empty_marker=empty_marker,
        )
        return cls(question_map=question_map)
