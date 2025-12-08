from pathlib import Path
from typing import Protocol, runtime_checkable

from ..serializations.base import DataBlob


@runtime_checkable
class DataSource(Protocol):
    def read(self) -> DataBlob: ...


class StringSource:
    def __init__(self, data: str, media_type: str = "text/plain", extension: str = "txt"):
        self._data = data.encode("utf-8")
        self._media_type = media_type
        self._extension = extension

    def read(self) -> DataBlob:
        return DataBlob(data=self._data, media_type=self._media_type, extension=self._extension)


class BytesSource:
    def __init__(self, data: bytes, media_type: str, extension: str):
        self._data = data
        self._media_type = media_type
        self._extension = extension

    def read(self) -> DataBlob:
        return DataBlob(data=self._data, media_type=self._media_type, extension=self._extension)


class FileSource:
    def __init__(self, path: Path, media_type: str | None = None):
        self._path = path
        self._media_type = media_type

    def read(self) -> DataBlob:
        data = self._path.read_bytes()
        ext = self._path.suffix.lstrip(".").lower()
        media_type = self._media_type or _guess_media_type(ext)
        return DataBlob(data=data, media_type=media_type, extension=ext)


def _guess_media_type(ext: str) -> str:
    return {
        "yaml": "application/yaml",
        "yml": "application/yaml",
        "json": "application/json",
        "csv": "text/csv",
        "tsv": "text/tab-separated-values",
        "txt": "text/plain",
    }.get(ext, "application/octet-stream")
