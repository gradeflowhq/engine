from collections.abc import Iterable
from typing import Literal

import yaml

from ...registry import submissions_saver_registry
from ..models import GradedSubmission
from .base import BaseSubmissionsSaver, SubmissionsSaverOutput


def save_graded_submissions_yaml(submissions: Iterable[GradedSubmission]) -> str:
    items = [gs.model_dump() for gs in submissions]
    return yaml.safe_dump(items, sort_keys=False)


@submissions_saver_registry.register_decorator("YAML")
class YamlSubmissionsSaver(BaseSubmissionsSaver):
    name: Literal["YAML"] = "YAML"

    def save(self, submissions: Iterable[GradedSubmission]) -> SubmissionsSaverOutput:
        return SubmissionsSaverOutput(
            data=save_graded_submissions_yaml(submissions),
            extension="yaml",
        )
