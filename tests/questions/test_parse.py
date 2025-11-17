from gradeflow_engine.questions import utils


def test_try_parse_number_int_and_float() -> None:
    assert utils.try_parse_number("7") == 7
    assert utils.try_parse_number("2.5") == 2.5


def test_parse_multi_value_defaults_and_options() -> None:
    s = " a ,b,c "
    assert utils.parse_multi_value(s) == ["a", "b", "c"]
    assert utils.parse_multi_value(s, trim_whitespace=False) == [" a ", "b", "c "]
    assert utils.parse_multi_value("A|B", delimiter="|", normalize_case=True) == [
        "a",
        "b",
    ]
