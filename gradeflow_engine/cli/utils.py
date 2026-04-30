from collections.abc import Callable
from typing import Any, TypeVar, overload

import typer
import yaml

T = TypeVar("T")


def parse_yaml_value(value: str) -> Any:
    try:
        return yaml.safe_load(value)
    except Exception:
        return value


@overload
def parse_kv_pairs(pairs: list[str] | None) -> dict[str, Any]: ...


@overload
def parse_kv_pairs(
    pairs: list[str] | None,
    value_parser: Callable[[str], T],
) -> dict[str, T]: ...


def parse_kv_pairs(
    pairs: list[str] | None,
    value_parser: Callable[[str], Any] = parse_yaml_value,
) -> dict[str, Any]:
    if not pairs:
        return {}
    out: dict[str, Any] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"Expected key=value, got: {item!r}")
        key, value = item.split("=", 1)
        out[key.strip()] = value_parser(value)
    return out
