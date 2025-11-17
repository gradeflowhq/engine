import textwrap

import pytest

from gradeflow_engine.core import (
    infer_question_set,
    list_available_question_set_loaders,
    list_available_question_set_savers,
    list_available_rubric_loaders,
    list_available_submissions_loaders,
    list_available_submissions_savers,
    load_question_set,
    load_rubric,
    load_submissions,
    run_pipeline,
    save_graded_submissions,
    save_question_set,
)
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.rules.result import QuestionResult
from gradeflow_engine.submissions.models import GradedSubmission


def test_registries_available():
    assert "YAML" in list_available_question_set_loaders()
    assert "YAML" in list_available_question_set_savers()
    assert "YAML" in list_available_rubric_loaders()
    assert "CSV" in list_available_submissions_loaders()
    assert "CSV" in list_available_submissions_savers()


def test_load_submissions_with_kwargs_csv():
    csv_data = textwrap.dedent(
        """\
        student_id,Q1,Q2
        s1,hello,42
        s2,world,3.14
        """
    )
    # Use kwargs validated by Pydantic on the loader class
    subs = load_submissions(
        csv_data,
        loader_name="CSV",
        student_id_column="student_id",
        answer_columns=["Q1", "Q2"],
    )
    assert len(subs) == 2
    assert subs[0].student_id == "s1"
    assert subs[0].raw_answer_map == {"Q1": "hello", "Q2": "42"}
    assert subs[1].raw_answer_map == {"Q1": "world", "Q2": "3.14"}


def test_infer_question_set_basic_text_vs_choice():
    csv_data = textwrap.dedent(
        """\
        student_id,Q1
        s1,alpha
        s2,beta
        s3,gamma
        s4,delta
        s5,epsilon
        s6,zeta
        """
    )
    subs = load_submissions(csv_data, loader_name="CSV")
    # With many distinct values, inference should prefer TEXT over CHOICE
    qset = infer_question_set(subs)
    assert isinstance(qset, QuestionSet)
    assert "Q1" in qset.question_map
    assert qset.question_map["Q1"].type == "TEXT"


def test_load_and_save_question_set_yaml_roundtrip():
    yaml_qset = textwrap.dedent(
        """\
        question_map:
          Q1:
            type: TEXT
            description: "Free text question"
          Q2:
            type: NUMERIC
            description: "Numeric question"
        """
    )
    qset = load_question_set(yaml_qset, loader_name="YAML")
    assert isinstance(qset, QuestionSet)
    assert set(qset.question_map.keys()) == {"Q1", "Q2"}
    out = save_question_set(qset, saver_name="YAML")
    assert out.extension == "yaml"
    assert "question_map" in out.data
    # load back to ensure stable serialization
    qset2 = load_question_set(out.data, loader_name="YAML")
    assert qset2 == qset


def test_load_rubric_yaml_and_grade_pipeline_with_explicit_qset():
    csv_data = textwrap.dedent(
        """\
        student_id,Q1
        s1,hello
        s2,world
        """
    )
    # Explicit QuestionSet (TEXT) to avoid CHOICE inference heuristic
    qset_yaml = textwrap.dedent(
        """\
        question_map:
          Q1:
            type: TEXT
        """
    )
    rubric_yaml = textwrap.dedent(
        """\
        rules:
          - type: EXACT_MATCH
            question_id: Q1
            max_points: 1
            answer: "hello"
        """
    )
    subs = load_submissions(csv_data, loader_name="CSV")
    qset = load_question_set(qset_yaml, loader_name="YAML")
    rubric = load_rubric(rubric_yaml, loader_name="YAML")

    result = run_pipeline(
        raw_submissions=subs,
        question_set=qset,
        rubric=rubric,
        saver_name="CSV",
        submissions_saver_kwargs={"include_total": True},
    )
    assert not result.validation_errors
    assert len(result.graded_submissions) == 2
    # s1 should get 1 point, s2 should get 0
    s1 = next(gs for gs in result.graded_submissions if gs.student_id == "s1")
    s2 = next(gs for gs in result.graded_submissions if gs.student_id == "s2")
    assert sum(r.points for r in s1.results) == 1.0
    assert sum(r.points for r in s2.results) == 0.0
    assert result.output is not None
    assert result.output.extension == "csv"
    assert "total_points" in result.output.data


def test_save_graded_submissions_csv_with_kwargs_headers():
    # Build a simple graded submission manually
    gs = GradedSubmission(
        student_id="s1",
        answer_map={"Q1": "hello"},
        results=[
            QuestionResult(
                question_id="Q1",
                output=True,
                passed=True,
                feedback="ok",
                rule="ExactMatchQuestionRule",
                points=1.0,
                max_points=1.0,
            )
        ],
    )
    out = save_graded_submissions(
        [gs],
        saver_name="CSV",
        student_id_column="id",
        include_answers=True,
        include_per_question_results=True,
        include_total=True,
    )
    assert out.extension == "csv"
    # Header should include custom student_id column and per-question fields
    header_line = out.data.splitlines()[0]
    assert "id" in header_line
    assert "Q1" in header_line
    assert "Q1__points" in header_line
    assert "total_points" in header_line


def test_run_pipeline_errors_on_conflicting_qset_inputs():
    csv_data = textwrap.dedent(
        """\
        student_id,Q1
        s1,hello
        """
    )
    with pytest.raises(ValueError):
        run_pipeline(
            submissions_data=csv_data,
            question_set=QuestionSet(question_map={}),
            question_set_data="question_map: {}",
        )


def test_run_pipeline_errors_when_no_submissions_source():
    with pytest.raises(ValueError):
        run_pipeline()
