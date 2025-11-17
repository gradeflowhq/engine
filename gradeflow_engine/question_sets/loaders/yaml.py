from typing import Literal

import yaml

from ...registry import question_set_loader_registry
from ..model import QuestionSet
from .base import BaseQuestionSetLoader


def load_question_set(yaml_data: str) -> QuestionSet:
    """
    Imports a question set from a YAML string.

    Args:
        yaml_data (str): The YAML string representing the question set.
    Returns:
        QuestionSet: The imported QuestionSet object.
    """
    data = yaml.safe_load(yaml_data)
    return QuestionSet.model_validate(data)


@question_set_loader_registry.register_decorator("YAML")
class YamlQuestionSetLoader(BaseQuestionSetLoader):
    name: Literal["YAML"] = "YAML"

    def load(self, data: str) -> QuestionSet:
        return load_question_set(data)
