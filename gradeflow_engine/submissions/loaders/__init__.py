from typing import Annotated

from pydantic import Discriminator

from .base import BaseSubmissionsLoader as BaseSubmissionsLoader
from .csv import CsvSubmissionsLoader

SubmissionsLoader = Annotated[CsvSubmissionsLoader, Discriminator("name")]
