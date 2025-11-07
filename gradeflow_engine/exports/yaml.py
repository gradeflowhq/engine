from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from .base import BaseExportConfig
from .registry import export_registry as registry
from .utils import write_yaml

if TYPE_CHECKING:
    from ..models import GradeOutput


class YamlExportConfig(BaseExportConfig):
    type: Literal["yaml"] = "yaml"
    indent: int = Field(default=2, description="YAML indentation level")


def yaml_export(results: "GradeOutput", file_path: Path | str, config: "YamlExportConfig") -> None:
    """Export the GradeOutput to YAML using the provided config."""
    data = results.model_dump(mode="json")
    write_yaml(data, str(file_path), indent=getattr(config, "indent", 2))


registry.register("yaml", yaml_export, YamlExportConfig)
