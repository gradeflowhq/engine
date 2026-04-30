from gradeflow_engine.adapters.common.examplify import (
    ExamplifyParseConfig,
    is_all_numeric_str,
    maybe_build_qid,
    points_from_row,
)


def test_examplify_common_edge_cases() -> None:
    cfg = ExamplifyParseConfig()

    assert maybe_build_qid({}, cfg) is None
    assert points_from_row({"Adjusted Points": "bad", "Original Points": "2.5"}) == 2.5
    assert is_all_numeric_str([]) is False
