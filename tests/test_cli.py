import textwrap
from pathlib import Path

from typer.testing import CliRunner

from gradeflow_engine import cli as cli_module

runner = CliRunner()


def test_list_components_shows_registered_entries() -> None:
    result = runner.invoke(cli_module.app, ["list"])
    assert result.exit_code == 0, result.output
    # Look for registry section titles
    assert "Question Set Serializers" in result.output
    assert "Rubric Serializers" in result.output
    assert "Graded Submissions Serializers" in result.output
    assert "Raw Submissions Adapters" in result.output
    assert "Question Set Adapters" in result.output
    assert "Rubric Adapters" in result.output
    # Canonical lowercase keys should be listed
    assert "yaml" in result.output
    assert "csv" in result.output
    assert "examplify" in result.output


def test_infer_command_prints_and_saves(tmp_path: Path) -> None:
    # Prepare a simple CSV submissions file
    csv_text = textwrap.dedent(
        """\
        student_id,Q1,Q2
        s1,alpha,1
        s2,beta,2
        s3,gamma,3
        """
    )
    sub_path = tmp_path / "subs.csv"
    sub_path.write_text(csv_text, encoding="utf-8")

    # Target path to save the inferred question set
    save_path = tmp_path / "inferred"

    result = runner.invoke(
        cli_module.app,
        [
            "infer",
            str(sub_path),
            "--raw-submissions-adapter",
            "csv",
            "--question-set-serializer",
            "yaml",
            "--save",
            str(save_path),
        ],
    )
    assert result.exit_code == 0, result.output
    # Should print inferred question set table and include question IDs
    assert "Inferred Question Set" in result.output
    assert "Q1" in result.output
    assert "Q2" in result.output

    # The inferred YAML should be saved with .yaml extension
    saved_file = save_path.with_suffix(".yaml")
    assert saved_file.exists()
    data = saved_file.read_text(encoding="utf-8")
    assert "question_map:" in data


def test_grade_command_with_rubric_and_save(tmp_path: Path) -> None:
    # Prepare CSV submissions
    csv_text = textwrap.dedent(
        """\
        student_id,Q1
        s1,hello
        s2,world
        """
    )
    sub_path = tmp_path / "subs.csv"
    sub_path.write_text(csv_text, encoding="utf-8")

    # Provide an explicit QuestionSet YAML (TEXT) to avoid inference surprises
    qset_yaml = textwrap.dedent(
        """\
        question_map:
          Q1:
            type: TEXT
        """
    )
    qset_path = tmp_path / "qset.yaml"
    qset_path.write_text(qset_yaml, encoding="utf-8")

    # Provide a rubric: exact match "hello"
    rubric_yaml = textwrap.dedent(
        """\
        rules:
          - type: TEXT_MATCH
            question_id: Q1
            max_points: 1
            answers: ["hello"]
        """
    )
    rubric_path = tmp_path / "rubric.yaml"
    rubric_path.write_text(rubric_yaml, encoding="utf-8")

    # Where to save graded CSV
    out_path = tmp_path / "graded"

    result = runner.invoke(
        cli_module.app,
        [
            "grade",
            "--submissions",
            str(sub_path),
            "--raw-submissions-adapter",
            "csv",
            "--question-set",
            str(qset_path),
            "--question-set-serializer",
            "yaml",
            "--rubric",
            str(rubric_path),
            "--rubric-serializer",
            "yaml",
            "--out-serializer",
            "csv",
            "--out",
            str(out_path),
        ],
    )

    assert result.exit_code == 0, result.output
    # Should print summaries
    assert "Question Set" in result.output
    assert "Parsed Submissions" in result.output
    # grading occurs and prints graded summary only when no validation errors and rubric provided
    assert "Graded Submissions" in result.output

    # Output file should be saved with .csv extension
    saved_file = out_path.with_suffix(".csv")
    assert saved_file.exists()
    out_csv = saved_file.read_text(encoding="utf-8")
    # The CSV should include totals (serializer includes totals by default)
    assert "total_points" in out_csv
    # Ensure both students are present
    assert "s1" in out_csv
    assert "s2" in out_csv


def test_cli_grade_prints_rubric_coverage(tmp_path: Path):
    # Prepare submissions CSV (two rows, one question Q1)
    submissions_csv = textwrap.dedent(
        """\
        student_id,Q1
        S1,foo
        S2,bar
        """
    )
    submissions_path = tmp_path / "subs.csv"
    submissions_path.write_text(submissions_csv, encoding="utf-8")

    # Provide a rubric YAML targeting Q1 with TEXT_MATCH
    rubric_yaml = textwrap.dedent(
        """\
        rules:
          - type: TEXT_MATCH
            question_id: Q1
            answers: [foo]
            max_points: 1
        """
    )
    rubric_path = tmp_path / "rubric.yaml"
    rubric_path.write_text(rubric_yaml, encoding="utf-8")

    # Let the CLI infer the question set; run grade command
    result = runner.invoke(
        cli_module.app,
        [
            "grade",
            "--submissions",
            str(submissions_path),
            "--raw-submissions-adapter",
            "csv",
            "--rubric",
            str(rubric_path),
            "--rubric-serializer",
            "yaml",
            "--out-serializer",
            "csv",
        ],
    )

    # CLI should succeed
    assert result.exit_code == 0, result.output

    # Check that coverage section is present and shows Q1 covered
    output = result.output
    assert "Rubric Coverage" in output
    assert "Covered by Rubric" in output
    # Expect 1 covered out of total inferred questions (should be 1 in this simple case)
    assert "Coverage" in output


def test_grade_command_with_adapter_and_serializer_kv(tmp_path: Path) -> None:
    # CSV uses custom id header;
    # pass kvs via repeated --raw-submissions-adapter-config and --out-serializer-config
    csv_text = textwrap.dedent(
        """\
        id,Q1
        s1,hello
        s2,world
        """
    )
    sub_path = tmp_path / "subs.csv"
    sub_path.write_text(csv_text, encoding="utf-8")

    qset_yaml = textwrap.dedent(
        """\
        question_map:
          Q1: {type: TEXT}
        """
    )
    qset_path = tmp_path / "qset.yaml"
    qset_path.write_text(qset_yaml, encoding="utf-8")

    rubric_yaml = textwrap.dedent(
        """\
        rules:
          - type: TEXT_MATCH
            question_id: Q1
            answers: ["hello"]
            max_points: 1
        """
    )
    rubric_path = tmp_path / "rubric.yaml"
    rubric_path.write_text(rubric_yaml, encoding="utf-8")

    out_path = tmp_path / "graded"

    result = runner.invoke(
        cli_module.app,
        [
            "grade",
            "--submissions",
            str(sub_path),
            "--raw-submissions-adapter",
            "csv",
            "--raw-submissions-adapter-config",
            "student_id_column=id",
            "--question-set",
            str(qset_path),
            "--question-set-serializer",
            "yaml",
            "--rubric",
            str(rubric_path),
            "--rubric-serializer",
            "yaml",
            "--out-serializer",
            "csv",
            "--out-serializer-config",
            "student_id_column=sid",
            "--out-serializer-config",
            "include_total=false",
            "--out",
            str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output

    saved = out_path.with_suffix(".csv")
    assert saved.exists()
    text = saved.read_text(encoding="utf-8")
    header = text.splitlines()[0].split(",")
    # Output CSV used custom student id column and totals disabled
    assert "sid" in header
    assert "student_id" not in header
    assert "total_points" not in header


def test_grade_command_qset_adapter_kv_include_thrown_out(tmp_path: Path) -> None:
    # Build a tiny Examplify-like CSV with a thrown-out row; include it with adapter kv
    examplify_csv = textwrap.dedent(
        """\
        Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer
        1,true,Choice,Ignore me,"x, y",
        """
    )
    subs_csv = textwrap.dedent(
        """\
        student_id,Q1
        s1,x
        """
    )
    subs_path = tmp_path / "subs.csv"
    subs_path.write_text(subs_csv, encoding="utf-8")
    qset_src = tmp_path / "exam_qset.csv"
    qset_src.write_text(examplify_csv, encoding="utf-8")

    # No rubric; just ensure the adapter includes the thrown-out question when configured
    result = runner.invoke(
        cli_module.app,
        [
            "grade",
            "--submissions",
            str(subs_path),
            "--raw-submissions-adapter",
            "csv",
            "--question-set-adapter-src",
            str(qset_src),
            "--question-set-adapter",
            "examplify",
            "--question-set-adapter-config",
            "config.include_thrown_out=true",
            "--out-serializer",
            "csv",
        ],
    )
    assert result.exit_code == 0, result.output


def test_grade_command_point_column_pass_through(tmp_path: Path) -> None:
    # Submissions CSV has a pre-scored column for Q1; rubric only targets Q2.
    # Q1 should appear in graded output with the pass-through points.
    csv_text = textwrap.dedent(
        """\
        student_id,Q1,Q2,q1_score
        s1,yes,hello,3.0
        s2,no,world,0.0
        """
    )
    sub_path = tmp_path / "subs.csv"
    sub_path.write_text(csv_text, encoding="utf-8")

    qset_yaml = textwrap.dedent(
        """\
        question_map:
          Q1: {type: TEXT}
          Q2: {type: TEXT}
        """
    )
    qset_path = tmp_path / "qset.yaml"
    qset_path.write_text(qset_yaml, encoding="utf-8")

    rubric_yaml = textwrap.dedent(
        """\
        rules:
          - type: TEXT_MATCH
            question_id: Q2
            answers: ["hello"]
            max_points: 1
        """
    )
    rubric_path = tmp_path / "rubric.yaml"
    rubric_path.write_text(rubric_yaml, encoding="utf-8")

    out_path = tmp_path / "graded"

    result = runner.invoke(
        cli_module.app,
        [
            "grade",
            "--submissions",
            str(sub_path),
            "--question-set",
            str(qset_path),
            "--question-set-serializer",
            "yaml",
            "--rubric",
            str(rubric_path),
            "--rubric-serializer",
            "yaml",
            "--point-column",
            "Q1=q1_score",
            "--out-serializer",
            "csv",
            "--out",
            str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output

    saved = out_path.with_suffix(".csv")
    assert saved.exists()
    lines = saved.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")

    # Q1 pass-through points column should be present
    assert "Q1__points" in header
    q1_pts_idx = header.index("Q1__points")

    s1_row = [r for r in lines[1:] if r.startswith("s1")][0].split(",")
    s2_row = [r for r in lines[1:] if r.startswith("s2")][0].split(",")

    assert s1_row[q1_pts_idx] == "3.0"
    assert s2_row[q1_pts_idx] == "0.0"


def test_infer_command_point_column_excluded_from_answers(tmp_path: Path) -> None:
    # The score column should not be inferred as a question.
    csv_text = textwrap.dedent(
        """\
        student_id,Q1,q1_score
        s1,yes,2.0
        s2,no,0.0
        """
    )
    sub_path = tmp_path / "subs.csv"
    sub_path.write_text(csv_text, encoding="utf-8")

    result = runner.invoke(
        cli_module.app,
        [
            "infer",
            str(sub_path),
            "--point-column",
            "Q1=q1_score",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Q1" in result.output
    assert "q1_score" not in result.output
