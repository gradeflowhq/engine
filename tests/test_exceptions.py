import pytest
from pydantic import ValidationError

from gradeflow_engine.exceptions import (
    AnswerParseError,
    DumpError,
    GradeFlowValidationError,
    LoadError,
    QuestionInferenceError,
    RubricError,
    RubricValidationError,
    UnknownQuestionError,
)
from gradeflow_engine.questions.models.text import TextQuestion


def test_rubric_validation_error_uses_validation_axis_only() -> None:
    assert issubclass(RubricValidationError, GradeFlowValidationError)
    assert not issubclass(RubricValidationError, RubricError)


def _validation_error() -> ValidationError:
    with pytest.raises(ValidationError) as exc_info:
        TextQuestion.model_validate({"max_points": "not-a-number"})
    return exc_info.value


def test_exception_constructors_and_validation_facade() -> None:
    validation_error = _validation_error()
    wrapped = GradeFlowValidationError(validation_error)

    assert wrapped.error_count() == validation_error.error_count()
    assert wrapped.json() == validation_error.json()

    assert DumpError("json", "bad").serializer == "json"
    assert LoadError("yaml", "bad").reason == "bad"

    answer_error = AnswerParseError("Q1", "raw", "nope")
    assert answer_error.question_id == "Q1"
    assert answer_error.raw_answer == "raw"

    assert UnknownQuestionError("QX").question_id == "QX"

    inference_error = QuestionInferenceError("Q1", "bad")
    assert inference_error.reason == "bad"
