from typing import Literal

import yaml

from ...registry import question_set_saver_registry
from ..model import QuestionSet
from .base import BaseQuestionSetSaver, QuestionSetSaverOutput


@question_set_saver_registry.register_decorator("YAML")
class YamlQuestionSetSaver(BaseQuestionSetSaver):
    name: Literal["YAML"] = "YAML"

    def save(self, question_set: QuestionSet) -> QuestionSetSaverOutput:
        yaml_data = yaml.safe_dump(question_set.model_dump())
        return QuestionSetSaverOutput(data=yaml_data, extension="yaml")
