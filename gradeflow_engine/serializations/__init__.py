from . import question_set as question_set
from . import rubric as rubric
from . import submissions as submissions
from .question_set.yaml import YamlQuestionSetSerializer
from .registries import (
    question_set_serializer_registry,
    rubric_serializer_registry,
    submissions_serializer_registry,
)
from .rubric.yaml import YamlRubricSerializer
from .submissions.csv import CsvSubmissionsSerializer
from .submissions.json import JsonSubmissionsSerializer
from .submissions.yaml import YamlSubmissionsSerializer


def register_builtins() -> None:
    question_set_serializer_registry.register("yaml", YamlQuestionSetSerializer, overwrite=True)
    rubric_serializer_registry.register("yaml", YamlRubricSerializer, overwrite=True)
    submissions_serializer_registry.register("csv", CsvSubmissionsSerializer, overwrite=True)
    submissions_serializer_registry.register("json", JsonSubmissionsSerializer, overwrite=True)
    submissions_serializer_registry.register("yaml", YamlSubmissionsSerializer, overwrite=True)
