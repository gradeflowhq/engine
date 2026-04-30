import pytest

from gradeflow_engine.questions.models.choice import ChoiceQuestion
from gradeflow_engine.questions.parser import MultiValuedParserConfig


def test_choice_parses_multiple_values_with_defaults() -> None:
    q = ChoiceQuestion()
    # default delimiter is ',' and trimming is True
    parsed = q.parse("A, B, C")
    assert parsed == {"A", "B", "C"}


def test_choice_normalize_and_custom_delimiter() -> None:
    q = ChoiceQuestion(config=MultiValuedParserConfig(delimiter="|", normalize_case=True))
    parsed = q.parse("Yes|NO|  Maybe ")
    assert parsed == {"yes", "no", "maybe"}


def test_choice_rejects_empty_option() -> None:
    with pytest.raises(ValueError, match="empty"):
        ChoiceQuestion(options={"A", ""})


def test_choice_rejects_duplicate_normalized_options() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        ChoiceQuestion(
            options={"A", "a"},
            config=MultiValuedParserConfig(normalize_case=True),
        )
