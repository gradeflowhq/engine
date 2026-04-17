from collections.abc import Iterable
from typing import Generic, TypeVar

from ..exceptions import SerializerNotFoundError
from ..question_sets.model import QuestionSet
from ..registry import Registry
from ..rubrics.model import Rubric
from ..submissions.models import Submission
from .base import Serializer

T = TypeVar("T")


class SerializerRegistry(Registry[type[Serializer[T]]], Generic[T]):
    def get(self, name: str) -> type[Serializer[T]]:
        key = self._normalize(name)
        try:
            return super().get(name)
        except KeyError as e:
            raise SerializerNotFoundError(key, self.available()) from e


question_set_serializer_registry: SerializerRegistry[QuestionSet] = SerializerRegistry(
    "question_set_serializer"
)
rubric_serializer_registry: SerializerRegistry[Rubric] = SerializerRegistry("rubric_serializer")

submissions_serializer_registry: SerializerRegistry[Iterable[Submission]] = SerializerRegistry(
    "submissions_serializer"
)
