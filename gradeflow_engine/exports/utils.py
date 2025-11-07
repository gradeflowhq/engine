"""
Shared I/O utilities for export modules.

Provides helpers to ensure parent directories exist and to write YAML
and CSV files in a small, well-tested way so other export modules can
be thin wrappers around these helpers.
"""

import csv
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel

if TYPE_CHECKING:
    # Imported only for type checking to avoid circular imports at runtime
    from ..models import GradeOutput


class Mapper(BaseModel):
    source: str
    transform: Callable[[Any], Any] | None = None


def _ensure_parent_dir(file_path: str) -> Path:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_yaml(data: dict[str, Any], file_path: str, indent: int = 2) -> None:
    path = _ensure_parent_dir(file_path)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=indent)


def write_csv(
    header: Sequence[str], rows: Iterable[Sequence[Any]], file_path: str, encoding: str = "utf-8"
) -> None:
    """Write CSV given a header and an iterable of row sequences.

    This helper keeps newline/encoding handling consistent across exports.
    """
    path = _ensure_parent_dir(file_path)
    with open(path, "w", encoding=encoding, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(list(header))
        for row in rows:
            writer.writerow(list(row))


def base_csv_export(
    results: "GradeOutput",
    file_path: Path | str,
    column_map: dict[str, Mapper],
    encoding: str = "utf-8",
) -> None:
    """Functional CSV exporter that extracts values from GradeOutput using a
    column_map of header->Mapper-like objects and writes the CSV.

    This mirrors the previous BaseCsvExport but lives in utils so it's
    available alongside write_csv.
    """

    def _get_attr(obj: object, source: str):
        cur = obj
        for part in source.split("."):
            if cur is None:
                return None
            if not hasattr(cur, part):
                return None
            cur = getattr(cur, part)
        return cur

    def _iter_rows() -> Iterable[Sequence[object]]:
        for res in results.results:
            row: list[object] = []
            for mapper in column_map.values():
                val = _get_attr(res, mapper.source)
                transform = getattr(mapper, "transform", None)
                if callable(transform):
                    val = transform(val)
                row.append(val)
            yield row

    write_csv(list(column_map.keys()), _iter_rows(), str(file_path), encoding=encoding)
