"""
Custom exceptions for the GradeFlow engine.

Hierarchy
---------
GradeFlowError                          # base for all engine errors
├── ConfigurationError                  # invalid pipeline / component configuration
├── SerializationError                  # base for serialization/deserialization failures
│   ├── SerializerNotFoundError         # registry lookup miss
│   ├── DumpError                       # dumps() failure
│   └── LoadError                       # loads() failure
├── AdapterError                        # base for adapter failures
│   ├── AdapterNotFoundError            # registry lookup miss
│   └── AdapterLoadError               # adapter.load() failure
├── SubmissionError                     # base for submission-related failures
│   ├── MissingStudentIdError           # student_id column absent in source row
│   ├── AnswerParseError                # raw answer could not be parsed
│   ├── UnknownQuestionError           # question ID not in question map
│   └── MissingAnswerError             # rule targets question ID not in submission's answer map
├── RubricError                         # base for rubric-related runtime failures
│   └── GradingError                   # failure during grading a submission
├── GradeFlowValidationError            # base for Pydantic model validation failures
│   ├── RubricValidationError           # rubric model validation failure
│   └── QuestionSetValidationError      # question set model validation failure
├── QuestionInferenceError              # failure during question-type inference
└── ExecutorError                       # base for code-execution failures
    ├── ExecutorTimeoutError            # child process exceeded time limit
    └── ExecutorRuntimeError           # child process exited non-zero / bad output
"""

from typing import Any

from pydantic import ValidationError
from pydantic_core import ErrorDetails

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class GradeFlowError(Exception):
    """Base class for all GradeFlow engine errors."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConfigurationError(GradeFlowError):
    """Raised when a pipeline or component is misconfigured."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


# ---------------------------------------------------------------------------
# Validation error
# ---------------------------------------------------------------------------


class GradeFlowValidationError(GradeFlowError):
    """Base class for validation errors in the GradeFlow engine."""

    def __init__(self, validation_error: ValidationError) -> None:
        self.validation_error = validation_error
        super().__init__(str(validation_error))

    @property
    def title(self) -> str:
        """Return the title of the validation error."""
        return self.validation_error.title

    def errors(self) -> list[ErrorDetails]:
        """Return the list of validation errors."""
        return self.validation_error.errors()

    def error_count(self) -> int:
        """Return the number of validation errors."""
        return self.validation_error.error_count()

    def json(self) -> str:
        """Return the JSON representation of the validation error."""
        return self.validation_error.json()


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class SerializationError(GradeFlowError):
    """Base class for serialization / deserialization errors."""


class SerializerNotFoundError(SerializationError):
    """Raised when a serializer key is not found in the registry."""

    def __init__(self, name: str, available: list[str]) -> None:
        self.name = name
        self.available = available
        super().__init__(
            f"Serializer '{name}' not found. "
            f"Available serializers: {', '.join(available) or '<none>'}"
        )


class DumpError(SerializationError):
    """Raised when serializing (dumping) an object fails."""

    def __init__(self, serializer: str, reason: str) -> None:
        self.serializer = serializer
        self.reason = reason
        super().__init__(f"Serializer '{serializer}' failed to dump: {reason}")


class LoadError(SerializationError):
    """Raised when deserializing (loading) data fails."""

    def __init__(self, serializer: str, reason: str) -> None:
        self.serializer = serializer
        self.reason = reason
        super().__init__(f"Serializer '{serializer}' failed to load: {reason}")


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


class AdapterError(GradeFlowError):
    """Base class for adapter errors."""


class AdapterNotFoundError(AdapterError):
    """Raised when an adapter key is not found in the registry."""

    def __init__(self, name: str, kind: str, available: list[str]) -> None:
        self.name = name
        self.kind = kind
        self.available = available
        super().__init__(
            f"{kind} adapter '{name}' not found. "
            f"Available adapters: {', '.join(available) or '<none>'}"
        )


class AdapterLoadError(AdapterError):
    """Raised when an adapter fails to load data from a source."""

    def __init__(self, adapter: str, reason: str) -> None:
        self.adapter = adapter
        self.reason = reason
        super().__init__(f"Adapter '{adapter}' failed to load: {reason}")


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------


class SubmissionError(GradeFlowError):
    """Base class for submission-related errors."""


class MissingStudentIdError(SubmissionError):
    """Raised when the student ID column is absent in a source row."""

    def __init__(self, column: str, row: dict[str, Any]) -> None:
        self.column = column
        self.row = row
        super().__init__(f"Student ID column '{column}' not found in row: {row}")


class AnswerParseError(SubmissionError):
    """Raised when a raw answer string cannot be parsed for a given question."""

    def __init__(self, question_id: str, raw_answer: str, reason: str) -> None:
        self.question_id = question_id
        self.raw_answer = raw_answer
        self.reason = reason
        super().__init__(
            f"Failed to parse answer for question '{question_id}' "
            f"(raw value: {raw_answer!r}): {reason}"
        )


class UnknownQuestionError(SubmissionError):
    """Raised when a question ID present in an answer map is not in the question set."""

    def __init__(self, question_id: str) -> None:
        self.question_id = question_id
        super().__init__(f"Unknown question ID in raw answer map: '{question_id}'")


class MissingAnswerError(SubmissionError):
    """Raised when a rule targets a question ID that is absent from the submission's answer map."""

    def __init__(self, question_id: str, student_id: str | None = None) -> None:
        self.question_id = question_id
        self.student_id = student_id
        location = f" (student: '{student_id}')" if student_id else ""
        super().__init__(f"No answer found for question '{question_id}'{location} in submission.")


# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------


class RubricError(GradeFlowError):
    """Base class for rubric-related errors."""


class RubricValidationError(GradeFlowValidationError):
    """Raised when a rubric fails validation."""


class GradingError(RubricError):
    """Raised when an error occurs while grading a submission."""

    def __init__(self, student_id: str, question_id: str, reason: str) -> None:
        self.student_id = student_id
        self.question_id = question_id
        self.reason = reason
        super().__init__(
            f"Grading failed for student '{student_id}', question '{question_id}': {reason}"
        )


# ---------------------------------------------------------------------------
# Question inference
# ---------------------------------------------------------------------------


class QuestionInferenceError(GradeFlowError):
    """Raised when question-type inference cannot be completed."""

    def __init__(self, question_id: str, reason: str) -> None:
        self.question_id = question_id
        self.reason = reason
        super().__init__(f"Question inference failed for question '{question_id}': {reason}")


class QuestionSetValidationError(GradeFlowValidationError):
    """Raised when a question set fails validation."""


# ---------------------------------------------------------------------------
# Code executor
# ---------------------------------------------------------------------------


class ExecutorError(GradeFlowError):
    """Base class for code-execution errors."""


class ExecutorTimeoutError(ExecutorError):
    """Raised when the child process exceeds the wall-clock time limit."""

    def __init__(self, time_limit_s: int) -> None:
        self.time_limit_s = time_limit_s
        super().__init__(f"Code execution timed out after {time_limit_s}s")


class ExecutorRuntimeError(ExecutorError):
    """Raised when the child process exits with a non-zero code or produces unparseable output."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Code execution failed: {reason}")
