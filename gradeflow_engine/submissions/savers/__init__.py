from typing import Annotated

from pydantic import Discriminator

from .base import BaseSubmissionsSaver as BaseSubmissionsSaver
from .csv_saver import CsvSubmissionsSaver
from .json_saver import JsonSubmissionsSaver
from .yaml_saver import YamlSubmissionsSaver

SubmissionsSaver = Annotated[
    CsvSubmissionsSaver | JsonSubmissionsSaver | YamlSubmissionsSaver, Discriminator("name")
]
