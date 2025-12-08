import json
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, Field

from ...submissions.models import GradedSubmission
from ..base import DataBlob, Serializer
from ..registries import graded_submissions_serializer_registry


class JsonGradedSubmissionsConfig(BaseModel):
    format: Literal["json"] = "json"
    ensure_ascii: bool = Field(default=False)


class _Encoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, set):
            return sorted(o)
        return super().default(o)


class JsonGradedSubmissionsSerializer(Serializer[Iterable[GradedSubmission]]):
    format = "json"
    media_type = "application/json"
    config: JsonGradedSubmissionsConfig = JsonGradedSubmissionsConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def dumps(self, submissions: Iterable[GradedSubmission]) -> DataBlob:
        items = [gs.model_dump() for gs in submissions]
        text = json.dumps(
            items,
            cls=_Encoder,
            ensure_ascii=self.config.ensure_ascii,
        )
        return DataBlob(data=text.encode("utf-8"), media_type=self.media_type, extension="json")

    def loads(self, blob) -> Iterable[GradedSubmission]:
        raise NotImplementedError("Deserializing graded submissions from JSON is not supported.")


graded_submissions_serializer_registry.register("json", JsonGradedSubmissionsSerializer)
