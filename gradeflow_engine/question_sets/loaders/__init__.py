from typing import Annotated

from pydantic import Discriminator

from .base import BaseQuestionSetLoader as BaseQuestionSetLoader
from .yaml import YamlQuestionSetLoader

QuestionSetLoader = Annotated[YamlQuestionSetLoader, Discriminator("name")]
