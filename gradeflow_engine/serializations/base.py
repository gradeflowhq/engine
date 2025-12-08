from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T")  # Domain model (e.g., QuestionSet, Rubric, list[GradedSubmission])


class DataBlob(BaseModel):
    """
    A unified representation of serialized data.
    - data: always bytes
    - media_type: IANA media type (e.g., application/yaml, application/json, text/csv)
    - extension: conventional file extension without leading dot (e.g., yaml, json, csv)
    """

    data: bytes
    media_type: str
    extension: str


class Serializer(Protocol, Generic[T]):
    """
    Minimal serializer protocol:
    - dumps: object -> DataBlob
    - loads: DataBlob -> object
    Implementations should be pure, stateless, and side-effect free.
    """

    format: str  # canonical key (e.g., 'yaml', 'json', 'csv')
    media_type: str  # e.g., 'application/yaml'

    def dumps(self, obj: T) -> DataBlob: ...

    def loads(self, blob: DataBlob) -> T: ...
