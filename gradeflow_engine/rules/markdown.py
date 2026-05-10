from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Literal

BACKTICK_RUN_RE = re.compile(r"`+")


def markdown_code(value: Any) -> str:
    text = str(value)
    longest_backtick_run = max(
        (len(match.group(0)) for match in BACKTICK_RUN_RE.finditer(text)),
        default=0,
    )
    fence = "`" * (longest_backtick_run + 1)
    if text.startswith(("`", " ")) or text.endswith(("`", " ")):
        text = f" {text} "
    return f"{fence}{text}{fence}"


def markdown_join(values: Iterable[Any], *, conjunction: Literal["and", "or"]) -> str:
    items = [markdown_code(value) for value in values]
    if len(items) <= 2:
        return f" {conjunction} ".join(items)
    return f"{', '.join(items[:-1])}, {conjunction} {items[-1]}"
