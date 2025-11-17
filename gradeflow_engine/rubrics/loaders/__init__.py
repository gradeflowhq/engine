from typing import Annotated

from pydantic import Discriminator

from .base import BaseRubricLoader as BaseRubricLoader
from .yaml import YamlRubricLoader

RubricLoader = Annotated[YamlRubricLoader, Discriminator("name")]
