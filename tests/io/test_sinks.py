from pathlib import Path

from gradeflow_engine.io.sinks import BytesSink, FileSink
from gradeflow_engine.serializations.base import DataBlob


class TestFileSink:
    def _blob(self, ext: str = "yaml") -> DataBlob:
        return DataBlob(data=b"content", media_type="application/yaml", extension=ext)

    def test_write_forces_extension(self, tmp_path: Path) -> None:
        out = tmp_path / "out.txt"
        sink = FileSink(out, force_extension=True)
        sink.write(self._blob("yaml"))
        assert (tmp_path / "out.yaml").read_bytes() == b"content"

    def test_write_preserves_matching_extension(self, tmp_path: Path) -> None:
        out = tmp_path / "out.yaml"
        sink = FileSink(out, force_extension=True)
        sink.write(self._blob("yaml"))
        assert out.read_bytes() == b"content"

    def test_write_no_force(self, tmp_path: Path) -> None:
        out = tmp_path / "out.txt"
        sink = FileSink(out, force_extension=False)
        sink.write(self._blob("yaml"))
        assert out.read_bytes() == b"content"


class TestBytesSink:
    def test_initially_none(self) -> None:
        sink = BytesSink()
        assert sink.blob is None

    def test_write_stores_blob(self) -> None:
        sink = BytesSink()
        blob = DataBlob(data=b"data", media_type="text/plain", extension="txt")
        sink.write(blob)
        assert sink.blob is blob
