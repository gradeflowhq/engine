import yaml

from gradeflow_engine.rules.result import QuestionResult
from gradeflow_engine.submissions.models import GradedSubmission
from gradeflow_engine.submissions.savers.yaml_saver import YamlSubmissionsSaver


def _make_graded_submission() -> GradedSubmission:
    return GradedSubmission(
        student_id="s1",
        answer_map={"Q1": "hello", "Q2": 42},
        results=[
            QuestionResult(
                question_id="Q1",
                output=True,
                passed=True,
                feedback="ok",
                rule="ExactMatchQuestionRule",
                points=1.0,
                max_points=1.0,
            ),
            QuestionResult(
                question_id="Q2",
                output=True,
                passed=True,
                feedback="in range",
                rule="NumericRangeQuestionRule",
                points=2.0,
                max_points=2.0,
            ),
        ],
    )


def test_yaml_saver_roundtrip_structure() -> None:
    gs = _make_graded_submission()
    saver = YamlSubmissionsSaver()
    out = saver.save([gs])

    assert out.extension == "yaml"
    assert isinstance(out.data, str)

    loaded = yaml.safe_load(out.data)
    # YAML saver emits a list of graded submission dicts
    assert isinstance(loaded, list)
    assert len(loaded) == 1
    item = loaded[0]

    # Basic keys present
    assert item["student_id"] == "s1"
    assert "answer_map" in item
    assert "results" in item

    # Check answer_map serialized faithfully
    amap = item["answer_map"]
    assert amap["Q1"] == "hello"
    assert amap["Q2"] == 42

    # Check one of the results
    res = item["results"][0]
    assert res["question_id"] == "Q1"
    assert res["passed"] is True
    assert res["points"] == 1.0
