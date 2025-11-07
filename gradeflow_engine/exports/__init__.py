"""Public exports for the gradeflow_engine.exports package."""

from typing import Annotated

from pydantic import Discriminator

from .canvas import CanvasExportConfig, canvas_export
from .csv import (
    DetailedCsvExportConfig,
    SummaryCsvExportConfig,
    detailed_csv_export,
    summary_csv_export,
)
from .registry import ExportRegistry, export_registry
from .utils import Mapper, base_csv_export, write_csv, write_yaml
from .yaml import YamlExportConfig, yaml_export

ExportConfig = Annotated[
    SummaryCsvExportConfig | DetailedCsvExportConfig | CanvasExportConfig | YamlExportConfig,
    Discriminator("type"),
]


__all__ = [
    "base_csv_export",
    "Mapper",
    "summary_csv_export",
    "detailed_csv_export",
    "canvas_export",
    "write_csv",
    "write_yaml",
    "SummaryCsvExportConfig",
    "DetailedCsvExportConfig",
    "CanvasExportConfig",
    "YamlExportConfig",
    "ExportConfig",
    "yaml_export",
    "export_registry",
    "ExportRegistry",
]
