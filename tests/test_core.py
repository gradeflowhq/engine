import textwrap

from gradeflow_engine.core import (
    PipelineResult,
    dump_question_set_to_blob,
    dump_submissions_to_blob,
    list_available_question_set_adapters,
    list_available_question_set_serializers,
    list_available_raw_submissions_adapters,
    list_available_rubric_adapters,
    list_available_rubric_serializers,
    list_available_submissions_serializers,
    load_question_set_from_blob,
    load_raw_submissions_via_adapter,
    run_pipeline,
)
from gradeflow_engine.io.sources import StringSource
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.serializations.base import DataBlob
from gradeflow_engine.submissions.models import RawSubmission, Submission


def test_registries_available() -> None:
    # Serializers
    assert "yaml" in list_available_question_set_serializers()
    assert "yaml" in list_available_rubric_serializers()
    assert "csv" in list_available_submissions_serializers()
    # Adapters
    assert "csv" in list_available_raw_submissions_adapters()
    assert "examplify" in list_available_question_set_adapters()
    assert "examplify" in list_available_rubric_adapters()


def test_load_raw_submissions_adapter_csv() -> None:
    csv_data = textwrap.dedent(
        """\
        student_id,Q1,Q2
        s1,hello,42
        s2,world,3.14
        """
    )
    subs = load_raw_submissions_via_adapter(
        StringSource(csv_data, media_type="text/csv", extension="csv"),
        adapter_name="csv",
    )
    assert len(subs) == 2
    assert subs[0].student_id == "s1"
    assert subs[0].raw_answer_map == {"Q1": "hello", "Q2": "42"}
    assert subs[1].raw_answer_map == {"Q1": "world", "Q2": "3.14"}


def test_infer_question_set_basic_text_vs_choice() -> None:
    csv_data = textwrap.dedent(
        """\
        student_id,Q1
        s1,alpha
        s2,beta
        s3,gamma
        s4,delta
        s5,epsilon
        s6,zeta
        s7,zeta 1
        s8,zeta 2
        s9,zeta 3
        s10,zeta 4
        """
    )
    subs = load_raw_submissions_via_adapter(
        StringSource(csv_data, media_type="text/csv", extension="csv"),
        adapter_name="csv",
    )
    # With many distinct values, inference should prefer TEXT over CHOICE
    qset = QuestionSet.infer(subs)
    assert isinstance(qset, QuestionSet)
    assert "Q1" in qset.question_map
    assert qset.question_map["Q1"].type == "TEXT"


def test_load_and_save_question_set_yaml_roundtrip() -> None:
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
    blob_in = DataBlob(
        data=yaml_qset.encode("utf-8"),
        media_type="application/yaml",
        extension="yaml",
    )
    qset = load_question_set_from_blob(blob_in, serializer_name="yaml")
    assert isinstance(qset, QuestionSet)
    assert set(qset.question_map.keys()) == {"Q1", "Q2"}

    # Confirm graded submissions serializers are present (sanity)
    blob_out = dump_submissions_to_blob([], serializer_name="csv")
    assert blob_out.extension == "csv"

    # Save and load question set via serializer
    out_blob = dump_question_set_to_blob(qset, serializer_name="yaml")
    assert out_blob.extension == "yaml"
    qset2 = load_question_set_from_blob(out_blob, serializer_name="yaml")
    assert qset2 == qset


def test_run_pipeline_with_explicit_qset_and_rubric_and_output() -> None:
    csv_data = textwrap.dedent(
        """\
        student_id,Q1
        s1,hello
        s2,world
        """
    )
    raw_subs = load_raw_submissions_via_adapter(
        StringSource(csv_data, media_type="text/csv", extension="csv"),
        adapter_name="csv",
    )
    # Explicit QuestionSet (TEXT) to avoid CHOICE inference heuristics
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
          - type: TEXT_MATCH
            question_id: Q1
            max_points: 1
            answers: ["hello"]
        """
    )

    # Run pipeline via serializer sources
    result: PipelineResult = run_pipeline(
        raw_submissions=raw_subs,
        question_set_source=StringSource(
            qset_yaml, media_type="application/yaml", extension="yaml"
        ),
        question_set_serializer_name="yaml",
        rubric_source=StringSource(rubric_yaml, media_type="application/yaml", extension="yaml"),
        rubric_serializer_name="yaml",
        graded_output_serializer_name="csv",
    )
    assert not result.validation_errors
    assert len(result.submissions) == 2
    # s1 should get 1 point, s2 should get 0
    s1 = next(gs for gs in result.submissions if gs.student_id == "s1")
    s2 = next(gs for gs in result.submissions if gs.student_id == "s2")
    assert sum(r.points for r in s1.result_map.values()) == 1.0
    assert sum(r.points for r in s2.result_map.values()) == 0.0
    assert result.output is not None
    assert result.output.extension == "csv"
    assert "total_points" in result.output.data.decode("utf-8")


def test_run_pipeline_errors_when_no_submissions_source() -> None:
    # Neither raw_submissions nor submissions_source provided -> ValueError
    try:
        _ = run_pipeline()
        raise AssertionError("Expected ValueError when no submissions source is provided")
    except ValueError:
        pass


def test_run_pipeline_includes_coverage_when_rubric_supplied() -> None:
    # Minimal data to exercise pipeline
    raw_submissions = [
        RawSubmission(student_id="S1", raw_answer_map={"Q1": "foo", "Q2": "baz"}),
        RawSubmission(student_id="S2", raw_answer_map={"Q1": "bar", "Q2": "qux"}),
    ]
    qset_yaml = textwrap.dedent(
        """\
        question_map:
          Q1: {type: TEXT}
          Q2: {type: TEXT}
        """
    )
    rubric_yaml = textwrap.dedent(
        """\
        rules:
          - type: TEXT_MATCH
            question_id: Q1
            answers: ["foo"]
            max_points: 1.0
        """
    )

    result: PipelineResult = run_pipeline(
        raw_submissions=raw_submissions,
        question_set_source=StringSource(
            qset_yaml, media_type="application/yaml", extension="yaml"
        ),
        question_set_serializer_name="yaml",
        rubric_source=StringSource(rubric_yaml, media_type="application/yaml", extension="yaml"),
        rubric_serializer_name="yaml",
        graded_output_serializer_name=None,  # avoid writing output
    )

    assert result.coverage is not None
    assert result.coverage.total == 2
    assert result.coverage.covered == 1
    assert result.coverage.percentage == 0.5
    assert result.coverage.covered_question_ids == {"Q1"}


def test_run_pipeline_coverage_none_without_rubric() -> None:
    raw_submissions = [
        RawSubmission(student_id="S1", raw_answer_map={"Q1": "foo"}),
    ]
    qset_yaml = textwrap.dedent(
        """\
        question_map:
          Q1: {type: TEXT}
        """
    )

    result = run_pipeline(
        raw_submissions=raw_submissions,
        question_set_source=StringSource(
            qset_yaml, media_type="application/yaml", extension="yaml"
        ),
        question_set_serializer_name="yaml",
        rubric_source=None,
        rubric_serializer_name=None,
        graded_output_serializer_name=None,
    )

    assert result.coverage is None


def test_core_raw_adapter_kwargs_custom_student_id_and_filter() -> None:
    # Verify adapter_kwargs are honored for CsvRawSubmissionsAdapter
    csv_data = textwrap.dedent(
        """\
        id,a,b,extra
        123,x,y,z
        456,m,n,o
        """
    )
    subs = load_raw_submissions_via_adapter(
        StringSource(csv_data, media_type="text/csv", extension="csv"),
        adapter_name="csv",
        adapter_kwargs={"student_id_column": "id", "answer_columns": ["a", "b"]},
    )
    assert len(subs) == 2
    assert subs[0].student_id == "123"
    assert subs[0].raw_answer_map == {"a": "x", "b": "y"}
    assert subs[1].raw_answer_map == {"a": "m", "b": "n"}


def test_core_dump_graded_submissions_serializer_kwargs_csv_config() -> None:
    # Verify serializer_kwargs are honored for CsvSubmissionsSerializer
    gs = Submission(
        student_id="s1",
        answer_map={"Q1": "hello"},
    )
    blob = dump_submissions_to_blob(
        [gs],
        serializer_name="csv",
        serializer_kwargs={"student_id_column": "id", "include_total": False},
    )
    assert blob.extension == "csv"
    text = blob.data.decode("utf-8")
    header = text.splitlines()[0].split(",")
    # Custom student ID column and no totals
    assert "id" in header
    assert "student_id" not in header
    assert "total_points" not in header


def test_run_pipeline_with_kwargs_for_adapters_and_serializers() -> None:
    # Use adapter kwargs to parse CSV with custom id column
    csv_data = textwrap.dedent(
        """\
        id,Q1
        s1,hello
        s2,world
        """
    )
    qset_yaml = textwrap.dedent(
        """\
        question_map:
          Q1: {type: TEXT}
        """
    )
    rubric_yaml = textwrap.dedent(
        """\
        rules:
          - type: TEXT_MATCH
            question_id: Q1
            answers: ["hello"]
            max_points: 1
        """
    )

    result: PipelineResult = run_pipeline(
        submissions_source=StringSource(csv_data, media_type="text/csv", extension="csv"),
        submissions_adapter_name="csv",
        submissions_adapter_kwargs={"student_id_column": "id"},
        question_set_source=StringSource(
            qset_yaml, media_type="application/yaml", extension="yaml"
        ),
        question_set_serializer_name="yaml",
        rubric_source=StringSource(rubric_yaml, media_type="application/yaml", extension="yaml"),
        rubric_serializer_name="yaml",
        graded_output_serializer_name="csv",
        graded_output_serializer_kwargs={"student_id_column": "sid", "include_total": True},
    )

    assert not result.validation_errors
    assert len(result.submissions) == 2
    # Check that the output CSV used the custom student_id column "sid"
    assert result.output is not None
    out_csv = result.output.data.decode("utf-8")
    header = out_csv.splitlines()[0]
    assert "sid" in header
    assert "student_id" not in header
