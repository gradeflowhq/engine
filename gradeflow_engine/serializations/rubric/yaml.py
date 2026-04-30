from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

from ...exceptions import DumpError, LoadError, RubricValidationError
from ...mixins import ConfigurableMixin
from ...rubrics.model import Rubric
from ..base import DataBlob, Serializer
from .utils import model_dump_minimal


class YamlRubricConfig(BaseModel):
    format: Literal["yaml"] = "yaml"


class YamlRubricSerializer(ConfigurableMixin[YamlRubricConfig], Serializer[Rubric]):
    format = "yaml"
    media_type = "application/yaml"
    config: YamlRubricConfig = YamlRubricConfig()

    def dumps(self, obj: Rubric) -> DataBlob:
        try:
            text = yaml.safe_dump(model_dump_minimal(obj), sort_keys=False)
        except yaml.YAMLError as e:
            raise DumpError("yaml", str(e)) from e
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="yaml")

    def loads(self, blob: DataBlob) -> Rubric:
        try:
            data = yaml.safe_load(blob.data.decode("utf-8")) or {}
            return Rubric.model_validate(data)
        except ValidationError as e:
            raise RubricValidationError(e) from e
        except Exception as e:
            raise LoadError("yaml", str(e)) from e
