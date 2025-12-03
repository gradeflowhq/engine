import math
from fractions import Fraction


def _try_parse_number(string: str) -> float | int:
    s = string.strip()
    # Try integer
    try:
        return int(s)
    except ValueError:
        pass

    # Try float (handles decimals, scientific notation)
    try:
        return float(s)
    except ValueError:
        pass

    # Try standard fractions "a/b" (no mixed numbers)
    try:
        return float(Fraction(s))
    except Exception as e:
        raise ValueError(f"Could not parse number: {string}") from e


def try_parse_number(string: str) -> float | int:
    maybe_number = _try_parse_number(string)
    if math.isnan(maybe_number):
        raise ValueError(f"Number is not a valid value: {string}")
    if not math.isfinite(maybe_number):
        raise ValueError(f"Number is not finite: {string}")
    return maybe_number


def parse_multi_value(
    string: str,
    delimiter: str = ",",
    normalize_case: bool = False,
    trim_whitespace: bool = True,
) -> list[str]:
    if normalize_case:
        string = string.lower()
    parsed_values = list(string.split(delimiter))
    if trim_whitespace:
        parsed_values = [value.strip() for value in parsed_values]
    return parsed_values


def is_empty_answer(raw_answer: str, empty_marker: str) -> bool:
    return raw_answer in [empty_marker, ""]
