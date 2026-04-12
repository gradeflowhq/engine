from pathlib import Path

from gradeflow_engine.io.sources import BytesSource, FileSource, StringSource


class TestStringSource:
    def test_read_returns_utf8_blob(self) -> None:
        src = StringSource("hello", media_type="text/plain", extension="txt")
        blob = src.read()
        assert blob.data == b"hello"
        assert blob.media_type == "text/plain"
        assert blob.extension == "txt"

    def test_default_media_type(self) -> None:
        src = StringSource("data")
        blob = src.read()
        assert blob.media_type == "text/plain"
        assert blob.extension == "txt"

    def test_unicode_encoding(self) -> None:
        src = StringSource("café")
        blob = src.read()
        assert blob.data == "café".encode()


class TestBytesSource:
    def test_read_passthrough(self) -> None:
        raw = b"\x00\x01\x02"
        src = BytesSource(raw, media_type="application/octet-stream", extension="bin")
        blob = src.read()
        assert blob.data == raw
        assert blob.media_type == "application/octet-stream"


class TestFileSource:
    def test_read_file(self, tmp_path: Path) -> None:
        f = tmp_path / "data.yaml"
        f.write_text("key: value")
        src = FileSource(f)
        blob = src.read()
        assert blob.data == b"key: value"
        assert blob.extension == "yaml"
        assert blob.media_type == "application/yaml"

    def test_custom_media_type_override(self, tmp_path: Path) -> None:
        f = tmp_path / "data.txt"
        f.write_text("stuff")
        src = FileSource(f, media_type="application/custom")
        blob = src.read()
        assert blob.media_type == "application/custom"

    def test_csv_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "grades.csv"
        f.write_text("a,b")
        blob = FileSource(f).read()
        assert blob.extension == "csv"
        assert blob.media_type == "text/csv"

    def test_unknown_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "data.xyz"
        f.write_bytes(b"binary")
        blob = FileSource(f).read()
        assert blob.media_type == "application/octet-stream"
