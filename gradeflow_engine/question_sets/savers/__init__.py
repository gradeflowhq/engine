from typing import Annotated

from pydantic import Discriminator

from .base import BaseQuestionSetSaver as BaseQuestionSetSaver
from .yaml import YamlQuestionSetSaver

QuestionSetSaver = Annotated[YamlQuestionSetSaver, Discriminator("name")]
