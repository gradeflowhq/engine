import json
from collections.abc import Iterable
from typing import Any, Literal

from ...registry import submissions_saver_registry
from ..models import GradedSubmission
from .base import BaseSubmissionsSaver, SubmissionsSaverOutput


class GradeflowJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, set):
            return sorted(o)  # type: ignore[return-value]
        return super().default(o)


def save_graded_submissions_json(submissions: Iterable[GradedSubmission]) -> str:
    items = [gs.model_dump() for gs in submissions]
    return json.dumps(
        items,
        cls=GradeflowJSONEncoder,
        separators=(",", ":"),
        ensure_ascii=False,
    )


@submissions_saver_registry.register_decorator("JSON")
class JsonSubmissionsSaver(BaseSubmissionsSaver):
    name: Literal["JSON"] = "JSON"

    def save(self, submissions: Iterable[GradedSubmission]) -> SubmissionsSaverOutput:
        return SubmissionsSaverOutput(
            data=save_graded_submissions_json(submissions),
            extension="json",
        )
