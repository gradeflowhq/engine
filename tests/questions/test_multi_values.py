from gradeflow_engine.questions.models.multi_valued import MultiValuedQuestion
from gradeflow_engine.questions.parser import MultiValuedParserConfig


def test_multi_values_parses_and_filters_numbers() -> None:
    q = MultiValuedQuestion()
    # Should parse values and filter those that are numeric (only keep strings that aren't numbers)
    parsed = q.parse("one, 2, three, 4.5, five")
    # Numeric values should be removed by parse_multi_valued_answer
    assert parsed == ["one", 2, "three", 4.5, "five"]


def test_multi_values_with_custom_options() -> None:
    q = MultiValuedQuestion(config=MultiValuedParserConfig(delimiter=";"))
    parsed = q.parse("alpha; beta ; 3; gamma")
    assert parsed == ["alpha", "beta", 3, "gamma"]
