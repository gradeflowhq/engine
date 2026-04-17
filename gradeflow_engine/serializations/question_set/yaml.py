from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

from ...exceptions import DumpError, LoadError, QuestionSetValidationError
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
        try:
            text = yaml.safe_dump(obj.model_dump())
        except yaml.YAMLError as e:
            raise DumpError("yaml", str(e)) from e
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="yaml")

    def loads(self, blob: DataBlob) -> QuestionSet:
        try:
            data = yaml.safe_load(blob.data.decode("utf-8")) or {}
            return QuestionSet.model_validate(data)
        except ValidationError as e:
            raise QuestionSetValidationError(e) from e
        except Exception as e:
            raise LoadError("yaml", str(e)) from e


question_set_serializer_registry.register("yaml", YamlQuestionSetSerializer)
