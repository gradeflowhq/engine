import json

from gradeflow_engine.rules.result import QuestionResult
from gradeflow_engine.submissions.models import GradedSubmission
from gradeflow_engine.submissions.savers.json_saver import JsonSubmissionsSaver


def _make_graded_submission() -> GradedSubmission:
    return GradedSubmission(
        student_id="s2",
        answer_map={"QX": {"y", "x"}},
        results=[
            QuestionResult(
                question_id="QX",
                output=False,
                passed=False,
                feedback="wrong",
                rule="MultipleChoiceQuestionRule",
                points=0.0,
                max_points=2.0,
            )
        ],
    )


def test_json_saver_compact_and_parseable() -> None:
    gs = _make_graded_submission()
    saver = JsonSubmissionsSaver()
    out = saver.save([gs])

    assert out.extension == "json"
    assert isinstance(out.data, str)

    # Should be valid JSON array of objects
    payload = json.loads(out.data)
    assert isinstance(payload, list)
    assert len(payload) == 1
    item = payload[0]

    assert item["student_id"] == "s2"
    assert "answer_map" in item
    assert "results" in item

    # Choice answer serialized as a list (JSON has no set type); exact order is not guaranteed
    answer = item["answer_map"]["QX"]
    assert isinstance(answer, list)
    assert set(answer) == {"x", "y"}

    res = item["results"][0]
    assert res["question_id"] == "QX"
    assert res["passed"] is False
    assert res["max_points"] == 2.0
