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
