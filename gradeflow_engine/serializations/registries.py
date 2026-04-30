from collections.abc import Iterable
from typing import Any, Generic, TypeVar

from ..exceptions import SerializerNotFoundError
from ..question_sets.model import QuestionSet
from ..registry import Registry
from ..rubrics.model import Rubric
from ..submissions.models import Submission
from .base import Dumper, Serializer

SerializerT = TypeVar("SerializerT", bound=Dumper[Any])


class SerializerRegistry(Registry[type[SerializerT]], Generic[SerializerT]):
    def _make_not_found_error(self, key: str, available: list[str]) -> Exception:
        return SerializerNotFoundError(key, available)


question_set_serializer_registry: SerializerRegistry[Serializer[QuestionSet]] = SerializerRegistry(
    "question_set_serializer"
)
rubric_serializer_registry: SerializerRegistry[Serializer[Rubric]] = SerializerRegistry(
    "rubric_serializer"
)

submissions_serializer_registry: SerializerRegistry[Dumper[Iterable[Submission]]] = (
    SerializerRegistry("submissions_serializer")
)
