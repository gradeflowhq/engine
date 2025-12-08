from typing import Literal

import yaml
from pydantic import BaseModel

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
        text = yaml.safe_dump(obj.model_dump())
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="yaml")

    def loads(self, blob: DataBlob) -> Rubric:
        data = yaml.safe_load(blob.data.decode("utf-8")) or {}
        return Rubric.model_validate(data)


rubric_serializer_registry.register("yaml", YamlRubricSerializer)
