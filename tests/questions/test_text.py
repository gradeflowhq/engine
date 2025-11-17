from gradeflow_engine.questions.models.text import TextQuestion


def test_text_returns_same_string() -> None:
    q = TextQuestion()
    assert q.parse("hello world") == "hello world"


def test_text_converts_non_string_to_str() -> None:
    q = TextQuestion()
    # integers and other types should be stringified
    assert q.parse(7) == "7"  # type: ignore
    assert q.parse(3.14) == "3.14"  # type: ignore


def test_text_preserves_whitespace() -> None:
    q = TextQuestion()
    value = "  leading and trailing  "
    assert q.parse(value) == value
