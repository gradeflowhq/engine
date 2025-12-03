from pydantic import BaseModel

from ..questions.models import Question
from ..questions.types import Answer, QuestionId
from ..submissions.models import RawSubmission, Submission
from .inference import (
    DEFAULT_CHOICE_DELIMITER,
    DEFAULT_CHOICE_NORMALIZE_CASE,
    DEFAULT_CHOICE_OPTION_LIMIT,
    DEFAULT_MULTI_VALUE_DELIMITER,
    infer_question_map,
)


def parse_raw_answer_map(
    question_map: dict[QuestionId, Question], raw_answer_map: dict[QuestionId, str]
) -> dict[QuestionId, Answer]:
    answer_map: dict[QuestionId, Answer] = {}
    for qid, raw_answer in raw_answer_map.items():
        question = question_map[qid]
        try:
            answer: Answer = question.parse(raw_answer)
        except ValueError as e:
            raise ValueError(f"Failed to parse answer for question {qid}: {e}") from e
        answer_map[qid] = answer
    return answer_map


def parse_raw_submission(
    question_map: dict[QuestionId, Question], raw_submission: RawSubmission
) -> Submission:
    answer_map = parse_raw_answer_map(question_map, raw_submission.raw_answer_map)
    parsed_submission = Submission(student_id=raw_submission.student_id, answer_map=answer_map)
    return parsed_submission


class QuestionSet(BaseModel):
    question_map: dict[QuestionId, Question]

    def parse(self, raw_submissions: list[RawSubmission]) -> list[Submission]:
        return [
            parse_raw_submission(self.question_map, raw_submission)
            for raw_submission in raw_submissions
        ]

    @classmethod
    def infer(
        cls,
        raw_submissions: list[RawSubmission],
        *,
        choice_delimiter: str = DEFAULT_CHOICE_DELIMITER,
        choice_option_limit: int = DEFAULT_CHOICE_OPTION_LIMIT,
        choice_normalize_case: bool = DEFAULT_CHOICE_NORMALIZE_CASE,
        multi_value_delimiter: str = DEFAULT_MULTI_VALUE_DELIMITER,
    ) -> "QuestionSet":
        if not raw_submissions:
            return cls(question_map={})
        question_map = infer_question_map(
            raw_submissions,
            choice_delimiter=choice_delimiter,
            choice_option_limit=choice_option_limit,
            choice_normalize_case=choice_normalize_case,
            multi_value_delimiter=multi_value_delimiter,
        )
        return cls(question_map=question_map)
