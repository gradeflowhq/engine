from collections.abc import Iterable
from typing import Literal

import yaml
from pydantic import BaseModel

from ...mixins import ConfigurableMixin
from ...submissions.models import Submission
from ..base import DataBlob, Dumper


class YamlSubmissionsConfig(BaseModel):
    format: Literal["yaml"] = "yaml"
    sort_keys: bool = False


class YamlSubmissionsSerializer(
    ConfigurableMixin[YamlSubmissionsConfig], Dumper[Iterable[Submission]]
):
    format = "yaml"
    media_type = "application/yaml"
    config: YamlSubmissionsConfig = YamlSubmissionsConfig()

    def dumps(self, submissions: Iterable[Submission]) -> DataBlob:
        items = [submission.model_dump() for submission in submissions]
        text = yaml.safe_dump(items, sort_keys=self.config.sort_keys)
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="yaml")
