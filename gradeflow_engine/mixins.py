from typing import Generic, TypeVar

from pydantic import BaseModel

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class ConfigurableMixin(Generic[ConfigT]):
    config: ConfigT

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)
