import csv
import re
from collections.abc import Iterable
from io import StringIO
from typing import Literal

from pydantic import BaseModel, Field

from ...questions.utils import parse_multi_value, try_parse_number

# Examplify constants
EMPTY_MARKER: str = "N/A"
TRIM_WHITESPACE: bool = True
CHOICE_DELIMITER: str = ","
CHOICE_NORMALIZE_CASE: bool = True
MULTI_VALUE_DELIMITER: str = "~"
ALTERNATIVES_DELIMITER: str = "|"
QID_PREFIX: str = "Q"

# Patterns for FITB and numeric checks
_blank_marker_re = re.compile(r"\{(\d+)\}\s*")
_numeric_like_re = re.compile(r"^\s*[-+]?\d+(\.\d+)?\s*$")
_fraction_like_re = re.compile(r"^\s*[-+]?\d+\s*/\s*\d+\s*$")


class ExamplifyBaseConfig(BaseModel):
    name: Literal["examplify"] = "examplify"
    format: Literal["csv"] = "csv"


class ExamplifyParseConfig(ExamplifyBaseConfig):
    # Applies to parsing/inference of QuestionSet
    include_thrown_out: bool = Field(default=False)
    parse_answer_string: bool = Field(
        default=False,
        description=("Parse numeric-like FITB blanks as NUMERIC; else treat all as TEXT."),
    )
    skip_empty_alternatives: bool = Field(
        default=True,
        description="Ignore empty tokens in alternatives (e.g., trailing '|').",
    )


class ExamplifyRuleConfig(ExamplifyParseConfig):
    # Adds rule behavior on top of parse config
    choice_mode: Literal["ALL", "ANY", "PARTIAL"] = Field(default="PARTIAL")
    multi_valued_mode: Literal["ALL", "ANY", "PARTIAL"] = Field(default="PARTIAL")


def make_dict_reader(data: str) -> csv.DictReader:
    return csv.DictReader(StringIO(data))


def get_str(row: dict[str, str | None], key: str) -> str:
    val = row.get(key)
    return (val or "").strip()


def build_qid(_: ExamplifyBaseConfig, seq: str) -> str:
    # Keep signature to avoid touching callers
    return f"{QID_PREFIX}{seq.strip()}"


def points_from_row(row: dict[str, str | None]) -> float:
    for key in ("Adjusted Points", "Original Points"):
        s = get_str(row, key)
        if not s:
            continue
        try:
            return float(s)
        except ValueError:
            continue
    return 0.0


def extract_blank_segments(answer: str) -> list[str]:
    """
    Parses FITB answer key in the format:
      {1} VALUE1, {2} VALUE2, ...
    where VALUE may contain commas and/or be 'VALA|VALB|...'.

    Rule:
    - The separator between entries is a comma immediately before the next marker {n},
      possibly with spaces around it.
    - Commas inside values are preserved.
    - A trailing comma at the end of the string (no next marker) is treated as part of the value.

    Returns the list of segment strings for each blank (VALUEi), trimmed of surrounding whitespace,
    and with only the separator comma (before the next marker) removed.
    """
    matches = list(_blank_marker_re.finditer(answer))

    segments_by_index: dict[int, str] = {}

    for i, m in enumerate(matches):
        idx = int(m.group(1))
        start = m.end()
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(answer)

        # Raw chunk between this marker and the next marker (or end)
        chunk = answer[start:next_start]

        # If there is a next marker, drop a trailing separator comma (with surrounding spaces)
        if i + 1 < len(matches):
            # Strip right-side whitespace to check for a trailing comma separator
            right_stripped = chunk.rstrip()
            if right_stripped.endswith(","):
                # Remove the trailing comma separator and any spaces around it
                # Keep the rest (including internal commas)
                # Find position of that trailing comma in the original chunk
                sep_pos = len(right_stripped) - 1
                # Keep everything before the separator comma
                chunk = right_stripped[:sep_pos]
        # For the last segment, do not strip trailing commas (they are part of the value)

        val = chunk.strip()
        segments_by_index[idx] = val

    return [segments_by_index[i] for i in sorted(segments_by_index)]


def split_alternatives(seg: str, *, skip_empty: bool) -> list[str]:
    tokens = parse_multi_value(
        seg, delimiter=ALTERNATIVES_DELIMITER, trim_whitespace=TRIM_WHITESPACE
    )
    if skip_empty:
        tokens = [t for t in tokens if t != ""]
    return list(set(tokens))


def is_all_numeric_str(values: Iterable[str]) -> bool:
    # Normalize and optionally skip empties
    vals = [v.strip() for v in values]
    if not vals:
        return False
    for v in vals:
        vv = v.replace(",", "").strip()
        if _numeric_like_re.match(vv) or _fraction_like_re.match(vv):
            continue
        try:
            float(vv)
        except ValueError:
            return False
    return True


def parse_number_str_list(vals: Iterable[str]) -> list[float | int]:
    # Fractions become floats; commas removed; optionally skip empty tokens
    out: set[float | int] = set()
    for v in vals:
        v_clean = v.replace(",", "").strip()
        out.add(try_parse_number(v_clean))
    return list(out)
