from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

from ...exceptions import DumpError, LoadError, RubricValidationError
from ...rubrics.model import Rubric
from ..base import DataBlob, Serializer
from ..registries import rubric_serializer_registry


class YamlRubricConfig(BaseModel):
    format: Literal["yaml"] = "yaml"


class YamlRubricSerializer(Serializer[Rubric]):
    format = "yaml"
    media_type = "application/yaml"
    config: YamlRubricConfig = YamlRubricConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def dumps(self, obj: Rubric) -> DataBlob:
        try:
            text = yaml.safe_dump(obj.model_dump())
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


rubric_serializer_registry.register("yaml", YamlRubricSerializer)
