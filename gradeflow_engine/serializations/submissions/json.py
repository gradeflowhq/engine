import json
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, Field

from ...mixins import ConfigurableMixin
from ...submissions.models import Submission
from ..base import DataBlob, Dumper


class JsonSubmissionsConfig(BaseModel):
    format: Literal["json"] = "json"
    ensure_ascii: bool = Field(default=False)


class _Encoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, set):
            return sorted(o)
        return super().default(o)


class JsonSubmissionsSerializer(
    ConfigurableMixin[JsonSubmissionsConfig], Dumper[Iterable[Submission]]
):
    format = "json"
    media_type = "application/json"
    config: JsonSubmissionsConfig = JsonSubmissionsConfig()

    def dumps(self, submissions: Iterable[Submission]) -> DataBlob:
        items = [submission.model_dump() for submission in submissions]
        text = json.dumps(
            items,
            cls=_Encoder,
            ensure_ascii=self.config.ensure_ascii,
        )
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="json")
