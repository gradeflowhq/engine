from collections.abc import Callable
from typing import TypedDict


class ExportEntry(TypedDict):
    func: Callable[..., None]
    config_model: type | None


class ExportRegistry:
    """Singleton-like registry for exporters (mirrors RuleRegistry design)."""

    _registry: dict[str, ExportEntry] = {}

    @classmethod
    def register(
        cls, name: str, func: Callable[..., None], config_model: type | None = None
    ) -> None:
        if name in cls._registry:
            raise KeyError(f"export already registered: {name}")
        cls._registry[name] = {"func": func, "config_model": config_model}

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._registry.pop(name, None)

    @classmethod
    def list(cls) -> dict[str, ExportEntry]:
        return dict(cls._registry)

    @classmethod
    def get_by_name(cls, name: str) -> ExportEntry:
        return cls._registry[name]

    @classmethod
    def get_multiple_by_config(cls, config_or_type: type | object) -> dict[str, ExportEntry]:
        if isinstance(config_or_type, type):
            ct = config_or_type
        else:
            ct = type(config_or_type)

        matches: dict[str, ExportEntry] = {}
        for name, entry in cls._registry.items():
            model = entry.get("config_model")
            if model is None:
                continue
            try:
                if model is ct and issubclass(ct, model):
                    matches[name] = entry
            except TypeError:
                continue
        return matches

    @classmethod
    def get_by_config(cls, config_or_type: type | object) -> ExportEntry:
        matches = cls.get_multiple_by_config(config_or_type)
        if not matches:
            raise KeyError(f"no export registered for config type {config_or_type}")
        if len(matches) > 1:
            raise KeyError(
                f"multiple exports match config type {config_or_type}: {list(matches.keys())}"
            )
        return next(iter(matches.values()))


# Singleton instance
export_registry = ExportRegistry()
