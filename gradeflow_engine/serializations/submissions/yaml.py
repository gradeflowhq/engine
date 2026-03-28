from collections.abc import Iterable
from typing import Literal

import yaml
from pydantic import BaseModel

from ...submissions.models import Submission
from ..base import DataBlob, Serializer
from ..registries import submissions_serializer_registry


class YamlSubmissionsConfig(BaseModel):
    format: Literal["yaml"] = "yaml"
    sort_keys: bool = False


class YamlSubmissionsSerializer(Serializer[Iterable[Submission]]):
    format = "yaml"
    media_type = "application/yaml"
    config: YamlSubmissionsConfig = YamlSubmissionsConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def dumps(self, submissions: Iterable[Submission]) -> DataBlob:
        items = [gs.model_dump() for gs in submissions]
        text = yaml.safe_dump(items, sort_keys=self.config.sort_keys)
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="yaml")

    def loads(self, blob):
        raise NotImplementedError("Deserializing submissions from YAML is not supported.")


submissions_serializer_registry.register("yaml", YamlSubmissionsSerializer)
