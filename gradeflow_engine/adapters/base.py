from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from ..exceptions import AdapterLoadError, GradeFlowError, GradeFlowValidationError
from ..io.sources import DataSource
from ..mixins import ConfigurableMixin

ConfigT = TypeVar("ConfigT", bound=BaseModel)
LoadedT = TypeVar("LoadedT")


class BaseAdapter(ConfigurableMixin[ConfigT], ABC, Generic[ConfigT, LoadedT]):
    name: ClassVar[str]
    config: ConfigT
    _validation_error_cls: ClassVar[type[GradeFlowValidationError]]

    def load(self, source: DataSource) -> LoadedT:
        try:
            return self._load(source)
        except ValidationError as e:
            raise self._validation_error_cls(e) from e
        except GradeFlowError:
            raise
        except Exception as e:
            raise AdapterLoadError(self.name, str(e)) from e

    @abstractmethod
    def _load(self, source: DataSource) -> LoadedT:
        raise NotImplementedError
