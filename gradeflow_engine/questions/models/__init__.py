from typing import Annotated

from pydantic import Field

from .choice import ChoiceQuestion
from .multi_valued import MultiValuedQuestion
from .numeric import NumericQuestion
from .text import TextQuestion

Question = Annotated[
    ChoiceQuestion | MultiValuedQuestion | TextQuestion | NumericQuestion,
    Field(discriminator="type"),
]
