import pytest
from pydantic import ValidationError

from gradeflow_engine.exceptions import (
    AnswerParseError,
    DumpError,
    ExecutorRuntimeError,
    GradeFlowValidationError,
    LoadError,
    MalformedCsvRowError,
    MissingStudentIdError,
    QuestionInferenceError,
    QuestionSetValidationError,
    RubricError,
    RubricValidationError,
    UnknownQuestionError,
)
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models.text import TextQuestion
from gradeflow_engine.rubrics.model import Rubric


def test_rubric_validation_error_uses_validation_axis_only() -> None:
    assert issubclass(RubricValidationError, GradeFlowValidationError)
    assert not issubclass(RubricValidationError, RubricError)


def _validation_error() -> ValidationError:
    with pytest.raises(ValidationError) as exc_info:
        TextQuestion.model_validate({"max_points": "not-a-number"})
    return exc_info.value


def _rubric_validation_error(data: object) -> RubricValidationError:
    with pytest.raises(ValidationError) as exc_info:
        Rubric.model_validate(data)
    return RubricValidationError(exc_info.value)


def _question_set_validation_error(data: object) -> QuestionSetValidationError:
    with pytest.raises(ValidationError) as exc_info:
        QuestionSet.model_validate(data)
    return QuestionSetValidationError(exc_info.value)


def test_exception_constructors_and_validation_facade() -> None:
    validation_error = _validation_error()
    wrapped = GradeFlowValidationError(validation_error)

    assert wrapped.error_count() == validation_error.error_count()
    assert wrapped.json() == validation_error.json()
    assert "validation error for" not in str(wrapped)
    assert "Input should be" not in str(wrapped)

    assert DumpError("json", "bad").serializer == "json"
    assert LoadError("yaml", "bad").reason == "bad"

    answer_error = AnswerParseError("Q1", "raw", "nope")
    assert answer_error.question_id == "Q1"
    assert answer_error.raw_answer == "raw"

    assert UnknownQuestionError("QX").question_id == "QX"

    inference_error = QuestionInferenceError("Q1", "bad")
    assert inference_error.reason == "bad"


def test_rubric_validation_error_message_is_user_friendly() -> None:
    error = _rubric_validation_error(
        {"rules": [{"type": "LENGTH", "question_id": "q1", "min_length": "x"}]}
    )

    assert str(error) == (
        "Rubric is invalid.\n- Rule 1 > Length > min length must be a whole number."
    )
    assert error.errors() == error.validation_error.errors()
    assert "Input should be" not in str(error)
    assert "validation error for" not in str(error)


def test_rubric_validation_error_explains_missing_and_unknown_rule_types() -> None:
    error = _rubric_validation_error(
        {"rules": [{}, {"type": "NOT_A_RULE", "question_id": "q1"}]}
    )
    message = str(error)

    assert message == (
        "Rubric is invalid.\n"
        "- Please select a valid rule for Rule 1.\n"
        "- Rule 2 has an unknown type 'NOT_A_RULE'."
    )


def test_question_set_validation_error_message_is_user_friendly() -> None:
    error = _question_set_validation_error({"question_map": {"q1": {}}})
    assert str(error) == "Question set is invalid.\n- Question map > q1 is missing a type."
    assert "Unable to extract tag" not in str(error)


def test_validation_location_keeps_uppercase_mapping_keys_readable() -> None:
    error = _question_set_validation_error({"question_map": {"Q_ID": {}}})
    assert error.messages == ["Question map > Q ID is missing a type."]


def test_submission_errors_do_not_dump_raw_rows() -> None:
    row = {"student_id": "", "answer": "yes", "private_notes": "extra context"}

    missing = MissingStudentIdError("student_id", row)
    malformed = MalformedCsvRowError(4, {"student_id": "s1", "q1": None}, ["q1"])

    assert missing.row == row
    assert str(missing) == "CSV row is missing a value in the student ID column 'student_id'."
    assert str(malformed) == (
        "CSV row 4 is malformed. Columns with missing values: q1. "
        "This usually means the row has too few cells or contains an unquoted newline."
    )


def test_executor_runtime_error_summarizes_python_tracebacks() -> None:
    raw_traceback = (
        "Traceback (most recent call last):\n"
        '  File "<string>", line 1, in <module>\n'
        "ZeroDivisionError: division by zero\n"
    )

    error = ExecutorRuntimeError(raw_traceback)

    assert error.reason == raw_traceback
    assert str(error) == "Code execution failed: ZeroDivisionError: division by zero"
    assert "Traceback" not in str(error)
