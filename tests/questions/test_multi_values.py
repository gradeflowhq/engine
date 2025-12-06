import pytest

from gradeflow_engine.questions.models.multi_valued import MultiValuedQuestion
from gradeflow_engine.questions.parser import MultiValuedParserConfig


def test_multi_values_parses_and_filters_numbers() -> None:
    q = MultiValuedQuestion(value_types=["TEXT", "NUMERIC", "TEXT", "NUMERIC", "TEXT"])
    parsed = q.parse("one, 2, three, 4.5, five")
    assert parsed == ["one", 2, "three", 4.5, "five"]


def test_multi_values_with_custom_options() -> None:
    q = MultiValuedQuestion(
        config=MultiValuedParserConfig(delimiter=";"),
        value_types=["TEXT", "TEXT", "NUMERIC", "TEXT"],
    )
    parsed = q.parse("alpha; beta ; 3; gamma")
    assert parsed == ["alpha", "beta", 3, "gamma"]


def test_multi_values_respects_value_types_and_empty_marker() -> None:
    # Configure custom delimiter and rely on default empty_marker "N/A"
    q = MultiValuedQuestion(
        config=MultiValuedParserConfig(delimiter=";"),
        value_types=["NUMERIC", "TEXT", "NUMERIC"],
    )
    # Second token is the empty marker -> None for TEXT
    # Third token is empty string -> None for NUMERIC
    parsed = q.parse("1; N/A; ")
    assert parsed == [1, None, None]


def test_multi_values_parses_fraction_and_scientific_notation() -> None:
    q = MultiValuedQuestion(
        value_types=["NUMERIC", "NUMERIC", "TEXT"],
    )
    # Fractions and scientific notation should be parsed numerically; text remains as-is
    parsed = q.parse("3/2, 1e2, hello")
    assert parsed == [1.5, 100.0, "hello"]


def test_multi_values_cardinality_mismatch_raises() -> None:
    q = MultiValuedQuestion(
        config=MultiValuedParserConfig(delimiter="|"),
        value_types=["TEXT", "NUMERIC", "TEXT"],
    )
    with pytest.raises(ValueError) as e:
        q.parse("only_one|2")  # only two tokens provided, expected three
    assert "Expected 3 values" in str(e.value)


def test_multi_values_trims_whitespace_and_uses_delimiter() -> None:
    q = MultiValuedQuestion(
        config=MultiValuedParserConfig(delimiter=";", trim_whitespace=True),
        value_types=["TEXT", "NUMERIC", "TEXT"],
    )
    parsed = q.parse(" alpha ; 42 ;  beta  ")
    assert parsed == ["alpha", 42, "beta"]
