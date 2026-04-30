import pytest
from pydantic import BaseModel

from gradeflow_engine.adapters.base import BaseAdapter
from gradeflow_engine.exceptions import (
    AdapterLoadError,
    ConfigurationError,
    GradeFlowValidationError,
)
from gradeflow_engine.io.sources import DataSource, StringSource


class _AdapterConfig(BaseModel):
    value: int = 1


class _Adapter(BaseAdapter[_AdapterConfig, str]):
    name = "dummy"
    config = _AdapterConfig()
    _validation_error_cls = GradeFlowValidationError

    def _load(self, source: DataSource) -> str:
        return source.read().data.decode("utf-8")


class _ValidationAdapter(_Adapter):
    def _load(self, source: DataSource) -> str:
        return _AdapterConfig.model_validate({"value": "bad"}).value  # type: ignore[return-value]


class _GradeFlowAdapter(_Adapter):
    def _load(self, source: DataSource) -> str:
        raise ConfigurationError("configured badly")


class _RuntimeAdapter(_Adapter):
    def _load(self, source: DataSource) -> str:
        raise RuntimeError("boom")


def test_base_adapter_load_error_paths() -> None:
    source = StringSource("ok")
    assert _Adapter(value=2).config.value == 2
    assert _Adapter().load(source) == "ok"

    with pytest.raises(GradeFlowValidationError):
        _ValidationAdapter().load(source)
    with pytest.raises(ConfigurationError):
        _GradeFlowAdapter().load(source)
    with pytest.raises(AdapterLoadError) as exc_info:
        _RuntimeAdapter().load(source)
    assert exc_info.value.adapter == "dummy"

    with pytest.raises(NotImplementedError):
        BaseAdapter._load(_Adapter(), source)
