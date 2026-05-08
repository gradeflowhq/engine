from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models import ChoiceQuestion, TextQuestion
from gradeflow_engine.submissions.models import RawSubmission


def make_submission(student_id: str, answers: dict[str, str]) -> RawSubmission:
    return RawSubmission(student_id=student_id, raw_answer_map=answers)


def test_question_set_drift_detects_question_and_choice_drift() -> None:
    question_set = QuestionSet(
        question_map={
            "Q1": TextQuestion(description="Keep me"),
            "Q2": ChoiceQuestion(options={"A"}, allow_multiple=False),
            "Q3": TextQuestion(description="No longer submitted"),
        }
    )
    raw_submissions = [
        make_submission("s1", {"Q1": "alpha", "Q2": "A, B", "Q4": "new"}),
        make_submission("s2", {"Q1": "beta", "Q2": "C", "Q4": "newer"}),
    ]

    drift = question_set.get_drift(raw_submissions)

    assert drift.has_drift is True
    assert drift.missing_question_ids == ["Q4"]
    assert drift.extra_question_ids == ["Q3"]
    assert len(drift.choice_option_drifts) == 1
    choice_drift = drift.choice_option_drifts[0]
    assert choice_drift.question_id == "Q2"
    assert choice_drift.missing_options == ["B", "C"]


def test_question_set_drift_is_clear_when_submissions_match() -> None:
    question_set = QuestionSet(
        question_map={
            "Q1": TextQuestion(),
            "Q2": ChoiceQuestion(options={"A", "B"}, allow_multiple=False),
        }
    )
    raw_submissions = [
        make_submission("s1", {"Q1": "alpha", "Q2": "A, B"}),
        make_submission("s2", {"Q1": "beta", "Q2": "B"}),
    ]

    drift = question_set.get_drift(raw_submissions)

    assert drift.has_drift is False
    assert drift.missing_question_ids == []
    assert drift.extra_question_ids == []
    assert drift.choice_option_drifts == []


def test_sync_from_submissions_preserves_existing_questions_and_updates_choice_options() -> None:
    question_set = QuestionSet(
        question_map={
            "Q1": TextQuestion(description="Custom prompt", max_points=2.5),
            "Q2": ChoiceQuestion(options={"A"}, allow_multiple=False, max_points=3.0),
            "Q3": TextQuestion(description="Remove me"),
        }
    )
    raw_submissions = [
        make_submission("s1", {"Q1": "alpha", "Q2": "A, B", "Q4": "1"}),
        make_submission("s2", {"Q1": "beta", "Q2": "C", "Q4": "2"}),
    ]

    synced = question_set.sync_from_submissions(raw_submissions)

    assert list(synced.question_map) == ["Q1", "Q2", "Q4"]
    assert synced.question_map["Q1"] == question_set.question_map["Q1"]

    q2 = synced.question_map["Q2"]
    assert isinstance(q2, ChoiceQuestion)
    assert q2.options == {"A", "B", "C"}
    assert q2.allow_multiple is False
    assert q2.max_points == 3.0

    assert "Q3" not in synced.question_map
    assert "Q4" in synced.question_map
