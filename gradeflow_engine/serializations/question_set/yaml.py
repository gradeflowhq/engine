from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

from ...exceptions import DumpError, LoadError, QuestionSetValidationError
from ...mixins import ConfigurableMixin
from ...question_sets.model import QuestionSet
from ..base import DataBlob, Serializer


class YamlQuestionSetConfig(BaseModel):
    format: Literal["yaml"] = "yaml"


class YamlQuestionSetSerializer(ConfigurableMixin[YamlQuestionSetConfig], Serializer[QuestionSet]):
    format = "yaml"
    media_type = "application/yaml"
    config: YamlQuestionSetConfig = YamlQuestionSetConfig()

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
