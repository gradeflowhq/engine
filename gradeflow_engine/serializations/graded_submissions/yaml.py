from collections.abc import Iterable
from typing import Literal

import yaml
from pydantic import BaseModel

from ...submissions.models import GradedSubmission
from ..base import DataBlob, Serializer
from ..registries import graded_submissions_serializer_registry


class YamlGradedSubmissionsConfig(BaseModel):
    format: Literal["yaml"] = "yaml"
    sort_keys: bool = False


class YamlGradedSubmissionsSerializer(Serializer[Iterable[GradedSubmission]]):
    format = "yaml"
    media_type = "application/yaml"
    config: YamlGradedSubmissionsConfig = YamlGradedSubmissionsConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def dumps(self, submissions: Iterable[GradedSubmission]) -> DataBlob:
        items = [gs.model_dump() for gs in submissions]
        text = yaml.safe_dump(items, sort_keys=self.config.sort_keys)
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="yaml")

    def loads(self, blob):
        raise NotImplementedError("Deserializing graded submissions from YAML is not supported.")


graded_submissions_serializer_registry.register("yaml", YamlGradedSubmissionsSerializer)
