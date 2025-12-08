import csv
from pathlib import Path

from gradeflow_engine.core import (
    load_question_set_via_adapter,
    load_raw_submissions_via_adapter,
    load_rubric_via_adapter,
)
from gradeflow_engine.io.sources import FileSource, StringSource
from gradeflow_engine.rules.models.multi_valued import MultiValuedQuestionRule

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ET_RESULTS_CSV = DATA_DIR / "ET_Results.csv"
ADJUST_SCORING_CSV = DATA_DIR / "Adjust_Scoring.csv"

TOLERANCE = 0.02  # acceptable point difference due to rounding differences


def _question_ids_from_adjust_scoring() -> list[str]:
    """
    Read Adjust_Scoring.csv to discover the Seq values present, and map them to QIDs.
    """
    with ADJUST_SCORING_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        qids: list[str] = []
        for row in reader:
            seq = row["Seq"]
            if not seq:
                continue
            qid = f"Q{seq}"
            qids.append(qid)
    # Deduplicate while preserving order
    seen = set()
    ordered = []
    for qid in qids:
        if qid not in seen:
            seen.add(qid)
            ordered.append(qid)
    return ordered


def test_examplify_imports_and_grading_match_et_results() -> None:
    # Discover QIDs from Adjust_Scoring (e.g., Q1..Q35)
    qids = _question_ids_from_adjust_scoring()
    assert qids, "No question IDs found in Adjust_Scoring.csv"

    # Read ET_Results and strip any UTF-8 BOMs (keep it simple)
    et_text = ET_RESULTS_CSV.read_text(encoding="utf-8")
    et_text_clean = et_text.replace("\ufeff", "")

    # Load raw submissions from ET_Results.csv via CSV adapter using cleaned text
    raw_submissions = load_raw_submissions_via_adapter(
        source=StringSource(et_text_clean, media_type="text/csv", extension="csv"),
        adapter_name="csv",
        adapter_kwargs={
            "student_id_column": "(ID)",
            "answer_columns": qids,  # only pull Q1..Qn answers
        },
    )
    assert raw_submissions, "No raw submissions loaded from ET_Results.csv"

    # Load QuestionSet via Examplify adapter (Adjust_Scoring.csv)
    qset = load_question_set_via_adapter(
        source=FileSource(ADJUST_SCORING_CSV),
        adapter_name="examplify",
    )
    assert qset.question_map, "QuestionSet should not be empty"

    # Load Rubric via Examplify adapter (Adjust_Scoring.csv)
    rubric = load_rubric_via_adapter(
        source=FileSource(ADJUST_SCORING_CSV),
        adapter_name="examplify",
    )
    assert rubric.rules, "Rubric should not be empty"

    # Modify rubric to set MultiValuedQuestionRule aggregation to "ALL"
    ALL_OR_NOTHING_QUESTIONS = {"Q6", "Q8"}
    for rule in rubric.rules:
        if (
            isinstance(rule, MultiValuedQuestionRule)
            and rule.question_id in ALL_OR_NOTHING_QUESTIONS
        ):
            rule.aggregation = "ALL"

    # Parse submissions and grade
    submissions = qset.parse(raw_submissions, strict=False)
    graded = rubric.grade(submissions, strict=False)
    assert graded, "No graded submissions produced"

    # Build lookups: student_id -> total points and per-question points
    engine_total_by_sid: dict[str, float] = {}
    engine_qpoints_by_sid: dict[str, dict[str, float]] = {}
    for gs in graded:
        qpoints: dict[str, float] = {}
        total = 0.0
        for res in gs.results:
            qpoints[res.question_id] = float(res.points)
            total += float(res.points)
        engine_total_by_sid[gs.student_id] = total
        engine_qpoints_by_sid[gs.student_id] = qpoints

    # Read ET_Results (cleaned) to compare "Pts" and per-question "QX Pts"
    reader = csv.DictReader(et_text_clean.splitlines())
    rows = list(reader)
    assert rows, "ET_Results.csv DictReader returned no rows"
    assert "Pts" in (reader.fieldnames or []), (
        "Expected total points column 'Pts' in ET_Results.csv"
    )

    for row in rows:
        sid = row["(ID)"]

        # Compare per-question points for all discovered qids where ET has a "QX Pts" column
        eng_qpoints = engine_qpoints_by_sid[sid]
        for qid in qids:
            col = f"{qid} Pts"

            val_str = row[col]
            if val_str == "":
                et_qp = 0.0
            else:
                et_qp = float(val_str)

            eng_qp = float(eng_qpoints[qid])
            assert abs(eng_qp - et_qp) < TOLERANCE, (
                f"Question {qid} points mismatch for student {sid}: "
                f"engine={eng_qp}, examplify={et_qp}"
            )

        # Compare totals
        et_total_str = row["Pts"]
        et_total = float(et_total_str)
        eng_total = engine_total_by_sid[sid]
        assert abs(eng_total - et_total) < TOLERANCE, (
            f"Total mismatch for student {sid}: engine={eng_total}, examplify={et_total}"
        )
