from typing import Annotated

from pydantic import Discriminator

from .csv import CsvSubmissionsConfig
from .json import JsonSubmissionsConfig
from .yaml import YamlSubmissionsConfig

SubmissionsSerializerConfig = Annotated[
    CsvSubmissionsConfig | JsonSubmissionsConfig | YamlSubmissionsConfig,
    Discriminator("format"),
]
