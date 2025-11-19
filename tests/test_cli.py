import textwrap
from pathlib import Path

from typer.testing import CliRunner

from gradeflow_engine import cli as cli_module

runner = CliRunner()


def test_list_components_shows_registered_entries() -> None:
    result = runner.invoke(cli_module.app, ["list"])
    assert result.exit_code == 0, result.output
    # Look for registry section titles and known keys
    assert "Question Set Loaders" in result.output
    assert "Question Set Savers" in result.output
    assert "Rubric Loaders" in result.output
    assert "Submissions Loaders" in result.output
    assert "Submissions Savers" in result.output
    # Keys registered by YAML/CSV modules
    assert "YAML" in result.output
    assert "CSV" in result.output


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

    # Target path to save inferred question set
    save_path = tmp_path / "inferred"
    result = runner.invoke(
        cli_module.app,
        [
            "infer",
            str(sub_path),
            "--submissions-loader",
            "CSV",
            "--question-set-saver",
            "YAML",
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
          - type: EXACT_MATCH
            question_id: Q1
            max_points: 1
            answer: "hello"
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
            "--submissions-loader",
            "CSV",
            "--question-set",
            str(qset_path),
            "--question-set-loader",
            "YAML",
            "--rubric",
            str(rubric_path),
            "--rubric-loader",
            "YAML",
            "--saver",
            "CSV",
            # pass saver kwargs via key=value
            "--saver-kv",
            "include_total=true",
            "--out",
            str(out_path),
        ],
    )

    assert result.exit_code == 0, result.output
    # Should print summaries
    assert "Question Set" in result.output
    assert "Parsed Submissions" in result.output
    assert "Graded Submissions" in result.output

    # Output file should be saved with .csv extension
    saved_file = out_path.with_suffix(".csv")
    assert saved_file.exists()
    out_csv = saved_file.read_text(encoding="utf-8")
    # The CSV should include totals because include_total=true was passed
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

    # Provide a rubric YAML targeting Q1 with EXACT_MATCH
    rubric_yaml = textwrap.dedent(
        """\
        rules:
          - type: EXACT_MATCH
            question_id: Q1
            answer: foo
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
            "--rubric",
            str(rubric_path),
            "--saver",
            "CSV",  # allow saver, but we won't pass --out, so it prints to stdout
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
    assert "Q1" in output or "Covered IDs" in output  # depending on your _print_coverage details
