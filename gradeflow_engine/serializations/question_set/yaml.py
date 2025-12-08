from typing import Literal

import yaml
from pydantic import BaseModel

from ...question_sets.model import QuestionSet
from ..base import DataBlob, Serializer
from ..registries import question_set_serializer_registry


class YamlQuestionSetConfig(BaseModel):
    format: Literal["yaml"] = "yaml"


class YamlQuestionSetSerializer(Serializer[QuestionSet]):
    format = "yaml"
    media_type = "application/yaml"
    config: YamlQuestionSetConfig = YamlQuestionSetConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def dumps(self, obj: QuestionSet) -> DataBlob:
        text = yaml.safe_dump(obj.model_dump())
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="yaml")

    def loads(self, blob: DataBlob) -> QuestionSet:
        data = yaml.safe_load(blob.data.decode("utf-8")) or {}
        return QuestionSet.model_validate(data)


question_set_serializer_registry.register("yaml", YamlQuestionSetSerializer)
