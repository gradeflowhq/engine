from collections.abc import Iterable
from typing import Generic, TypeVar

from ..question_sets.model import QuestionSet
from ..registry import Registry
from ..rubrics.model import Rubric
from ..submissions.models import Submission
from .base import Serializer

T = TypeVar("T")


class SerializerRegistry(Registry[type[Serializer[T]]], Generic[T]):
    pass


question_set_serializer_registry: SerializerRegistry[QuestionSet] = SerializerRegistry(
    "question_set_serializer"
)
rubric_serializer_registry: SerializerRegistry[Rubric] = SerializerRegistry("rubric_serializer")

submissions_serializer_registry: SerializerRegistry[Iterable[Submission]] = SerializerRegistry(
    "submissions_serializer"
)
