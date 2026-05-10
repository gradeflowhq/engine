"""User-facing formatting helpers for engine errors."""

from typing import Any

from pydantic_core import ErrorDetails

_MAX_REASON_LENGTH = 500
_NUMERIC_UNION_BRANCH_LOC_PARTS = {"int", "float"}


def format_reason(reason: str) -> str:
    """Return a compact, bounded reason string."""
    compact = " ".join(str(reason).strip().split())
    if not compact:
        return "Unknown error."
    if len(compact) <= _MAX_REASON_LENGTH:
        return compact
    return f"{compact[: _MAX_REASON_LENGTH - 1]}..."


def format_traceback_reason(reason: str) -> str:
    """Return the useful error line from a Python traceback, if present."""
    lines = [line.strip() for line in reason.splitlines() if line.strip()]
    if "Traceback (most recent call last):" not in lines:
        return format_reason(reason)

    for line in reversed(lines):
        if (
            not line.startswith(("File ", "^", "~"))
            and line != "Traceback (most recent call last):"
        ):
            return format_reason(line)
    return "Python code raised an error."


def format_validation_error_details(errors: list[ErrorDetails]) -> list[str]:
    """Return user-friendly messages for Pydantic validation errors."""
    return list(dict.fromkeys(_format_validation_error(error) for error in errors))


def format_validation_messages(subject: str, messages: list[str]) -> str:
    """Return a validation summary from preformatted detail messages."""
    if not messages:
        return f"{subject} is invalid."
    return "\n".join([f"{subject} is invalid.", *(f"- {message}" for message in messages)])


def _format_validation_error(error: ErrorDetails) -> str:
    loc_parts, is_numeric_union_branch = _strip_numeric_union_branch(error.get("loc", ()))
    loc = _format_validation_location(loc_parts)
    error_type = str(error.get("type") or "")
    ctx = error.get("ctx")
    context = ctx if isinstance(ctx, dict) else {}
    input_value = error.get("input")

    if is_numeric_union_branch and error_type in {
        "int_parsing",
        "int_type",
        "float_parsing",
        "float_type",
    }:
        return f"{loc} must be a number."
    if _is_blank_rule_selection_error(error_type, loc_parts, input_value, context):
        return _format_rule_selection_message(loc)
    if error_type == "missing":
        return f"{loc} is required."
    if error_type == "union_tag_not_found":
        return f"{loc} is missing a type."
    if error_type == "union_tag_invalid":
        tag = context.get("tag")
        if _is_blank_discriminator_tag(tag):
            return f"{loc} is missing a type."
        return f"{loc} has an unknown type {tag!r}."
    if error_type in {"int_parsing", "int_type"}:
        return f"{loc} must be a whole number."
    if error_type in {"float_parsing", "float_type"}:
        return f"{loc} must be a number."
    if error_type in {"string_type", "string_sub_type"}:
        return f"{loc} must be text."
    if error_type == "bool_type":
        return f"{loc} must be true or false."
    if error_type == "list_type":
        return f"{loc} must be a list."
    if error_type in {"dict_type", "model_attributes_type", "model_type"}:
        return f"{loc} must be an object."
    if error_type == "set_type":
        return f"{loc} must be a set."
    if error_type == "literal_error":
        expected = context.get("expected")
        if expected:
            return f"{loc} must be one of: {expected}."
        return f"{loc} has an unsupported value."
    if error_type == "greater_than_equal":
        return f"{loc} must be at least {context.get('ge')}."
    if error_type == "greater_than":
        return f"{loc} must be greater than {context.get('gt')}."
    if error_type == "less_than_equal":
        return f"{loc} must be at most {context.get('le')}."
    if error_type == "less_than":
        return f"{loc} must be less than {context.get('lt')}."
    if error_type == "too_short":
        return f"{loc} must contain at least {context.get('min_length')} items."
    if error_type == "too_long":
        return f"{loc} must contain at most {context.get('max_length')} items."
    if error_type == "value_error":
        return f"{loc} is invalid: {format_reason(_context_error_message(context))}"

    message = _strip_pydantic_prefix(str(error.get("msg") or ""))
    if message:
        return f"{loc} is invalid: {format_reason(message)}"
    return f"{loc} is invalid."


def _strip_numeric_union_branch(loc: object) -> tuple[object, bool]:
    if (
        isinstance(loc, tuple | list)
        and loc
        and loc[-1] in _NUMERIC_UNION_BRANCH_LOC_PARTS
    ):
        return loc[:-1], True
    return loc, False


def _is_blank_discriminator_tag(tag: object) -> bool:
    return tag in {None, "", "None"}


def _is_blank_rule_selection_error(
    error_type: str,
    loc: object,
    input_value: object,
    context: dict[str, Any],
) -> bool:
    if not _loc_targets_rule(loc):
        return False

    if error_type == "union_tag_not_found":
        return input_value == {}
    if error_type == "union_tag_invalid":
        return _is_blank_discriminator_tag(context.get("tag"))
    if error_type in {"model_attributes_type", "model_type"}:
        return input_value is None or input_value == ""
    return False


def _loc_targets_rule(loc: object) -> bool:
    if not isinstance(loc, tuple | list):
        return False

    parts = list(loc)
    for index, part in enumerate(parts):
        if part == "rule":
            return True
        if part == "rules" and index + 1 < len(parts) and isinstance(parts[index + 1], int):
            return True
    return False


def _format_rule_selection_message(loc: str) -> str:
    if loc == "Rule":
        return "Please select a valid rule."
    return f"Please select a valid rule for {loc}."


def _format_validation_location(loc: object) -> str:
    if not isinstance(loc, tuple | list):
        return "Value"

    parts = list(loc)
    output: list[str] = []
    index = 0

    while index < len(parts):
        part = parts[index]

        if isinstance(part, str) and index + 1 < len(parts) and isinstance(parts[index + 1], int):
            item_index = parts[index + 1]
            index_label = _format_collection_item_part(part, item_index)
            index += 2
            if index < len(parts) and _is_discriminator_part(
                parts[index],
                _next_part(parts, index),
            ):
                output.append(index_label)
                output.append(_format_discriminator_part(parts[index]))
                index += 1
                continue
            output.append(index_label)
            continue

        if isinstance(part, int):
            index_label = f"[{part + 1}]"
            index += 1
            if index < len(parts) and _is_discriminator_part(
                parts[index],
                _next_part(parts, index),
            ):
                index_label = f"{index_label} {_format_discriminator_part(parts[index])}"
                index += 1
            output.append(index_label)
            continue

        if _is_discriminator_part(part, _next_part(parts, index)):
            output.append(_format_discriminator_part(part))
        elif isinstance(part, str):
            output.append(_humanize_path_part(part))

        index += 1

    label = " > ".join(output) or "Value"
    return label[:1].upper() + label[1:]


def _next_part(parts: list[object], index: int) -> object | None:
    next_index = index + 1
    return parts[next_index] if next_index < len(parts) else None


def _is_discriminator_part(part: object, next_part: object | None) -> bool:
    if not isinstance(part, str) or next_part is None:
        return False
    return _is_type_tag_part(part) and _is_field_path_part(next_part)


def _is_field_path_part(part: object) -> bool:
    return isinstance(part, str) and bool(part) and not _is_type_tag_part(part)


def _is_type_tag_part(part: str) -> bool:
    return part.isupper() or _is_pascal_case_part(part)


def _is_pascal_case_part(part: str) -> bool:
    return part[:1].isupper() and any(char.islower() for char in part) and "_" not in part


def _format_discriminator_part(part: object) -> str:
    return _humanize_path_part(str(part)).title()


def _format_collection_item_part(part: str, item_index: int) -> str:
    return f"{_singularize_humanized_path_part(part).title()} {item_index + 1}"


def _singularize_humanized_path_part(part: str) -> str:
    words = _humanize_path_part(part).split()
    if not words:
        return "Item"
    words[-1] = _singularize_word(words[-1])
    return " ".join(words)


def _singularize_word(word: str) -> str:
    if word.endswith("ies") and len(word) > 3:
        return f"{word[:-3]}y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 1:
        return word[:-1]
    return word


def _humanize_path_part(part: str) -> str:
    return part.replace("_", " ")


def _strip_pydantic_prefix(message: str) -> str:
    for prefix in ("Value error, ", "Assertion failed, ", "Input should be "):
        if message.startswith(prefix):
            return message.removeprefix(prefix)
    return message


def _context_error_message(context: dict[str, Any]) -> str:
    error = context.get("error")
    return str(error) if error else "invalid value"
