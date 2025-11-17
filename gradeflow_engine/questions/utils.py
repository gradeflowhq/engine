def try_parse_number(string: str) -> float | int:
    try:
        return int(string)
    except ValueError:
        return float(string)


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
