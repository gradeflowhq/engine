from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T")  # Domain model (e.g., QuestionSet, Rubric, list[GradedSubmission])
DumpT = TypeVar("DumpT", contravariant=True)
LoadT = TypeVar("LoadT", covariant=True)


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


class Dumper(Protocol[DumpT]):
    format: str  # canonical key (e.g., 'yaml', 'json', 'csv')
    media_type: str  # e.g., 'application/yaml'

    def dumps(self, obj: DumpT) -> DataBlob: ...


class Loader(Protocol[LoadT]):
    format: str  # canonical key (e.g., 'yaml', 'json', 'csv')
    media_type: str  # e.g., 'application/yaml'

    def loads(self, blob: DataBlob, *, strict: bool = True) -> LoadT: ...


class Serializer(Dumper[T], Loader[T], Protocol[T]):
    """
    Bidirectional serializer protocol.

    Output-only serializers should implement Dumper[T] instead.
    """
