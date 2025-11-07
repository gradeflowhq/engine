from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .base import BaseCsvExportConfig
from .registry import export_registry as registry
from .utils import Mapper, base_csv_export

if TYPE_CHECKING:
    from ..models import GradeOutput


class CanvasExportConfig(BaseCsvExportConfig):
    type: Literal["csv.canvas"] = "csv.canvas"


def canvas_export(
    results: "GradeOutput", file_path: Path | str, config: "CanvasExportConfig"
) -> None:
    """Export results to a Canvas-compatible CSV using the shared base exporter."""
    # Canvas expects a header like: ["SIS User ID", "<Assignment Name>"]
    metadata = getattr(results, "metadata", {}) or {}
    assignment_name = metadata.get("rubric_name", "Assignment")

    # Build column map for base_csv_export: header -> Mapper
    col_map: dict[str, Mapper] = {
        "SIS User ID": Mapper(source="student_id"),
        assignment_name: Mapper(
            source="total_points", transform=lambda v: f"{v:.2f}" if v is not None else ""
        ),
    }

    base_csv_export(
        results=results,
        file_path=file_path,
        column_map=col_map,
        encoding=getattr(config, "encoding", "utf-8"),
    )


registry.register("csv.canvas", canvas_export, CanvasExportConfig)
