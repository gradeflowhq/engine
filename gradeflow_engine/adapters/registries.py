from typing import Generic, Protocol, TypeVar

from ..exceptions import AdapterNotFoundError
from ..io.sources import DataSource
from ..question_sets.model import QuestionSet
from ..registry import Registry
from ..rubrics.model import Rubric
from ..submissions.models import RawSubmission

T = TypeVar("T")


class AdapterRegistry(Registry[type[T]], Generic[T]):
    def get(self, name: str) -> type[T]:
        key = self._normalize(name)
        try:
            return super().get(name)
        except KeyError as e:
            raise AdapterNotFoundError(key, self._kind, self.available()) from e


class QuestionSetAdapter(Protocol):
    def load(self, source: DataSource) -> QuestionSet: ...


class RawSubmissionsAdapter(Protocol):
    def load(self, source: DataSource) -> list[RawSubmission]: ...


class RubricAdapter(Protocol):
    def load(self, source: DataSource) -> Rubric: ...


question_set_adapter_registry: AdapterRegistry[QuestionSetAdapter] = AdapterRegistry(
    "question_set_adapter"
)

raw_submissions_adapter_registry: AdapterRegistry[RawSubmissionsAdapter] = AdapterRegistry(
    "raw_submissions_adapter"
)

rubric_adapter_registry: AdapterRegistry[RubricAdapter] = AdapterRegistry("rubric_adapter")
