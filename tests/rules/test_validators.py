import pytest

from gradeflow_engine.rules.validators import (
    is_choice,
    is_empty,
    is_multi_valued,
    is_numeric,
    is_single_valued,
    is_text,
    validate_answer_type,
)


class TestTypeGuards:
    def test_is_empty(self) -> None:
        assert is_empty(None) is True
        assert is_empty(0) is False
        assert is_empty("") is False

    def test_is_numeric_excludes_bool(self) -> None:
        assert is_numeric(42) is True
        assert is_numeric(3.14) is True
        assert is_numeric(True) is False
        assert is_numeric(False) is False

    def test_is_numeric_rejects_strings(self) -> None:
        assert is_numeric("42") is False

    def test_is_text_includes_numbers(self) -> None:
        assert is_text("hello") is True
        assert is_text(42) is True
        assert is_text(3.14) is True

    def test_is_text_rejects_bool_and_none(self) -> None:
        assert is_text(True) is False
        assert is_text(None) is False

    def test_is_single_valued(self) -> None:
        assert is_single_valued("a") is True
        assert is_single_valued(1) is True
        assert is_single_valued(None) is True
        assert is_single_valued([1]) is False

    def test_is_choice(self) -> None:
        assert is_choice({"a", "b"}) is True
        assert is_choice(set()) is True
        assert is_choice({1, 2}) is False  # non-string elements
        assert is_choice(["a"]) is False

    def test_is_multi_valued(self) -> None:
        assert is_multi_valued(["a", 1, None]) is True
        assert is_multi_valued([]) is True
        assert is_multi_valued("a") is False
        assert is_multi_valued([{"a": 1}]) is False  # dict not single-valued


class TestValidateAnswerType:
    def test_valid_text(self) -> None:
        assert validate_answer_type("hello", frozenset({"TEXT"})) == "hello"

    def test_valid_numeric(self) -> None:
        assert validate_answer_type(42, frozenset({"NUMERIC"})) == 42

    def test_valid_choice(self) -> None:
        assert validate_answer_type({"a", "b"}, frozenset({"CHOICE"})) == {"a", "b"}

    def test_incompatible_type_raises(self) -> None:
        with pytest.raises(TypeError, match="not compatible"):
            validate_answer_type("text", frozenset({"NUMERIC"}))

    def test_unknown_question_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown question type"):
            validate_answer_type("x", frozenset({"UNKNOWN"}))  # type: ignore[arg-type]

    def test_multi_type_accepts_first_match(self) -> None:
        # "hello" is valid for TEXT but not NUMERIC
        assert validate_answer_type("hello", frozenset({"NUMERIC", "TEXT"})) == "hello"
