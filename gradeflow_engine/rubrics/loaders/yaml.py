from typing import Literal

import yaml

from ...registry import rubric_loader_registry
from ..model import Rubric
from .base import BaseRubricLoader


def load_rubric(yaml_data: str) -> Rubric:
    """
    Imports a rubric from a YAML string.

    Args:
        yaml_data (str): The YAML string representing the rubric.
    Returns:
        Rubric: The imported Rubric object.
    """
    data = yaml.safe_load(yaml_data)
    return Rubric.model_validate(data)


@rubric_loader_registry.register_decorator("YAML")
class YamlRubricLoader(BaseRubricLoader):
    name: Literal["YAML"] = "YAML"

    def load(self, data: str) -> Rubric:
        return load_rubric(data)
