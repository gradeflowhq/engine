from typing import Annotated

from pydantic import Discriminator

from .base import BaseSubmissionsSaver as BaseSubmissionsSaver
from .csv import CsvSubmissionsSaver

SubmissionsSaver = Annotated[CsvSubmissionsSaver, Discriminator("name")]
