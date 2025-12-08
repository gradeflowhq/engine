from typing import Annotated

from pydantic import Discriminator

from .csv import CsvGradedSubmissionsConfig
from .json import JsonGradedSubmissionsConfig
from .yaml import YamlGradedSubmissionsConfig

GradedSubmissionsSerializerConfig = Annotated[
    CsvGradedSubmissionsConfig | JsonGradedSubmissionsConfig | YamlGradedSubmissionsConfig,
    Discriminator("format"),
]
