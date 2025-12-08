from pathlib import Path
from typing import Protocol, runtime_checkable

from ..serializations.base import DataBlob


@runtime_checkable
class DataSink(Protocol):
    def write(self, blob: DataBlob) -> None: ...


class FileSink:
    def __init__(self, path: Path, force_extension: bool = True):
        self._path = path
        self._force_extension = force_extension

    def write(self, blob: DataBlob) -> None:
        path = self._path
        if self._force_extension and path.suffix.lstrip(".").lower() != blob.extension.lower():
            path = path.with_suffix(f".{blob.extension}")
        path.write_bytes(blob.data)


class BytesSink:
    def __init__(self) -> None:
        self.blob: DataBlob | None = None

    def write(self, blob: DataBlob) -> None:
        self.blob = blob
