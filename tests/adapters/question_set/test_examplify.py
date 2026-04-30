from pathlib import Path

from gradeflow_engine.adapters.question_set.examplify import ExamplifyQuestionSetAdapter
from gradeflow_engine.core import load_question_set_via_adapter
from gradeflow_engine.io.sources import FileSource, StringSource
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.questions.models import ChoiceQuestion, TextQuestion
from gradeflow_engine.questions.models.multi_valued import MultiValuedQuestion
from gradeflow_engine.questions.models.numeric import NumericQuestion


def test_choice_question_options_allow_multiple_and_normalization() -> None:
    # Use quoted Original Answer to preserve comma within one cell
    csv_text: str = (
        "Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer\n"
        '1,false,Choice,Pick colors,"Red , blue  ",\n'
    )
    qset: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert "Q1" in qset.question_map
    q = qset.question_map["Q1"]
    assert isinstance(q, ChoiceQuestion)
    # Constants: normalize case True, trim whitespace True
    assert q.options == {"red", "blue"}
    # allow_multiple autodetected since Original Answer had two tokens
    assert q.allow_multiple is True
    assert q.max_points == 1.0  # no points column in CSV → default


def test_choice_single_token_allows_multiple_false() -> None:
    csv_text: str = (
        "Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer\n"
        "2,false,Choice,Pick one,Green,\n"
    )
    qset: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    q = qset.question_map["Q2"]
    assert isinstance(q, ChoiceQuestion)
    assert q.options == {"green"}
    assert q.allow_multiple is False
    assert q.max_points == 1.0  # no points column in CSV → default


def test_fitb_single_numeric_vs_text_and_multi_blanks_value_types() -> None:
    # Default parse_answer_string=False => numeric-like blanks treated as TEXT
    csv_num: str = (
        "Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer\n"
        '3,false,Fill in the Blank,Enter number,"{1} 42",\n'
    )
    qset_num: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_num, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"parse_answer_string": False},
    )
    assert isinstance(qset_num.question_map["Q3"], TextQuestion)
    assert qset_num.question_map["Q3"].max_points == 1.0

    # Text single blank remains TEXT
    csv_txt: str = (
        "Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer\n"
        '4,false,Fill in the Blank,Enter text,"{1} ans",\n'
    )
    qset_txt: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_txt, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"parse_answer_string": False},
    )
    assert isinstance(qset_txt.question_map["Q4"], TextQuestion)
    assert qset_txt.question_map["Q4"].max_points == 1.0

    # Multi blanks: with default parse_answer_string=False, all positions forced to TEXT
    csv_multi: str = (
        "Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer\n"
        '5,false,Fill in the Blank,Two blanks,"{1} a | b, {2} 1 | 2",\n'
    )
    qset_multi: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_multi, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"parse_answer_string": False},
    )
    q5 = qset_multi.question_map["Q5"]
    assert isinstance(q5, MultiValuedQuestion)
    assert q5.value_types == ["TEXT", "TEXT"]
    assert q5.max_points == 1.0


def test_fitb_numeric_inference_when_enabled() -> None:
    # parse_answer_string=True => numeric-like single blank -> NumericQuestion
    csv_num: str = (
        "Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer\n"
        '6,false,Fill in the Blank,Enter number,"{1} 42",\n'
    )
    qset_num: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_num, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"parse_answer_string": True},
    )
    assert isinstance(qset_num.question_map["Q6"], NumericQuestion)
    assert qset_num.question_map["Q6"].max_points == 1.0

    # Multi blanks: per-position inference when enabled
    csv_multi: str = (
        "Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer\n"
        '7,false,Fill in the Blank,Two blanks,"{1} a | b, {2} 1 | 2",\n'
    )
    qset_multi: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_multi, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"parse_answer_string": True},
    )
    q7 = qset_multi.question_map["Q7"]
    assert isinstance(q7, MultiValuedQuestion)
    assert q7.value_types == ["TEXT", "NUMERIC"]
    assert q7.max_points == 1.0


def test_thrown_out_rows_skipped_by_default_and_included_with_config() -> None:
    csv_thrown_out: str = (
        "Seq,ThrowOut,Type,Item Text,Original Answer,Adjusted Answer\n"
        '8,true,Choice,Ignore me,"x, y",\n'
    )
    # Default adapter skips thrown-out
    qset_skip: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_thrown_out, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert "Q8" not in qset_skip.question_map

    # Explicitly include thrown-out via adapter instance with config
    qset_inc = load_question_set_via_adapter(
        StringSource(csv_thrown_out, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"include_thrown_out": True},
    )
    assert "Q8" in qset_inc.question_map
    assert isinstance(qset_inc.question_map["Q8"], ChoiceQuestion)
    assert qset_inc.question_map["Q8"].max_points == 1.0  # no points column → default


def _example_csv_path() -> Path:
    tests_dir = Path(__file__).resolve().parent.parent.parent
    return tests_dir / "data" / "Adjust_Scoring.csv"


def test_question_set_from_full_csv_defaults_and_inference() -> None:
    """
    Default behavior: parse_answer_string=False
    - Choice normalization and allow_multiple autodetect
    - FITB single and multi blanks treated as TEXT (multi-valued positions all TEXT)
    """
    csv_path = _example_csv_path()
    qset: QuestionSet = load_question_set_via_adapter(
        FileSource(csv_path),
        adapter_name="examplify",
    )

    # Choice normalization and allow_multiple autodetect across multiple rows
    q1 = qset.question_map["Q1"]
    assert isinstance(q1, ChoiceQuestion)
    assert q1.allow_multiple is True
    assert {"b", "c", "f", "g"} <= q1.options
    assert q1.max_points == 2.0

    q2 = qset.question_map["Q2"]
    assert isinstance(q2, ChoiceQuestion)
    assert q2.allow_multiple is False
    assert q2.options == {"a"}
    assert q2.max_points == 1.0

    q3 = qset.question_map["Q3"]
    assert isinstance(q3, ChoiceQuestion)
    assert q3.allow_multiple is True
    assert {"a", "c", "d"} <= q3.options
    assert q3.max_points == 1.0

    q4 = qset.question_map["Q4"]
    assert isinstance(q4, ChoiceQuestion)
    # Options should include adjusted tokens too (adapter collects observed options)
    assert {"a", "b", "c", "e"} <= q4.options
    assert q4.max_points == 2.0

    q5 = qset.question_map["Q5"]
    assert isinstance(q5, ChoiceQuestion)
    assert q5.allow_multiple is True
    assert {"a", "c", "d", "e"} <= q5.options
    assert q5.max_points == 2.0

    # FITB rows default to TEXT (single and multi)
    # Multi-valued FITB
    q6 = qset.question_map["Q6"]
    assert isinstance(q6, MultiValuedQuestion)
    assert q6.value_types == ["TEXT", "TEXT"]
    assert q6.max_points == 2.0

    q8 = qset.question_map["Q8"]
    assert isinstance(q8, MultiValuedQuestion)
    assert q8.value_types == ["TEXT", "TEXT"]
    assert q8.max_points == 2.0

    q22 = qset.question_map["Q22"]
    assert isinstance(q22, MultiValuedQuestion)
    assert q22.value_types == ["TEXT", "TEXT"]

    # Single-blank FITB as TEXT
    q7 = qset.question_map["Q7"]
    assert isinstance(q7, TextQuestion)
    assert q7.max_points == 2.0
    q11 = qset.question_map["Q11"]
    assert isinstance(q11, MultiValuedQuestion)
    assert q11.value_types == ["TEXT", "TEXT"]
    assert q11.max_points == 2.0
    q13 = qset.question_map["Q13"]
    assert isinstance(q13, TextQuestion)
    assert q13.max_points == 1.0
    q14 = qset.question_map["Q14"]
    assert isinstance(q14, TextQuestion)
    assert q14.max_points == 2.0
    q18 = qset.question_map["Q18"]
    assert isinstance(q18, TextQuestion)
    assert q18.max_points == 1.0
    q19 = qset.question_map["Q19"]
    assert isinstance(q19, TextQuestion)
    assert q19.max_points == 2.0
    q23 = qset.question_map["Q23"]
    assert isinstance(q23, TextQuestion)
    assert q23.max_points == 1.0
    q24 = qset.question_map["Q24"]
    assert isinstance(q24, TextQuestion)
    assert q24.max_points == 1.0


def test_question_set_from_full_csv_parse_enabled_numeric_inference() -> None:
    """
    With parse_answer_string=True:
    - Multi-blank numeric row: NUMERIC per position (Q6, Q8, Q22)
    - Single blank numeric-like: NumericQuestion (Q13, Q18, Q19, Q23, Q24)
    - Textual FITB remains TEXT (Q7, Q11, Q14)
    """
    csv_path = _example_csv_path()
    qset: QuestionSet = load_question_set_via_adapter(
        FileSource(csv_path),
        adapter_name="examplify",
        adapter_kwargs={"parse_answer_string": True},
    )

    # Multi-blank numeric rows -> NUMERIC per position
    q6 = qset.question_map["Q6"]
    assert isinstance(q6, MultiValuedQuestion)
    assert q6.value_types == ["NUMERIC", "NUMERIC"]
    assert q6.max_points == 2.0

    q8 = qset.question_map["Q8"]
    assert isinstance(q8, MultiValuedQuestion)
    assert q8.value_types == ["NUMERIC", "NUMERIC"]
    assert q8.max_points == 2.0

    q22 = qset.question_map["Q22"]
    assert isinstance(q22, MultiValuedQuestion)
    assert q22.value_types == ["NUMERIC", "NUMERIC"]

    # Single-blank numeric-like -> NumericQuestion
    q13 = qset.question_map["Q13"]
    assert isinstance(q13, NumericQuestion)
    assert q13.max_points == 1.0
    q18 = qset.question_map["Q18"]
    assert isinstance(q18, NumericQuestion)
    assert q18.max_points == 1.0
    q19 = qset.question_map["Q19"]
    assert isinstance(q19, NumericQuestion)
    assert q19.max_points == 2.0
    q23 = qset.question_map["Q23"]
    assert isinstance(q23, NumericQuestion)
    assert q23.max_points == 1.0
    q24 = qset.question_map["Q24"]
    assert isinstance(q24, NumericQuestion)
    assert q24.max_points == 1.0

    # Textual FITB remains TEXT
    q7 = qset.question_map["Q7"]
    assert isinstance(q7, TextQuestion)
    assert q7.max_points == 2.0
    q11 = qset.question_map["Q11"]
    assert isinstance(q11, MultiValuedQuestion)
    assert q11.value_types == ["TEXT", "TEXT"]
    assert q11.max_points == 2.0
    q14 = qset.question_map["Q14"]
    assert isinstance(q14, TextQuestion)
    assert q14.max_points == 2.0


def test_question_set_include_thrown_out_and_skip_full_credit() -> None:
    """
    Additional coverage for include_thrown_out=True and GiveFullCreditToAllETs=True.
    These cases are not present in the full CSV; we exercise them via inline data.
    """
    # Thrown-out row should be excluded by default, included when configured
    csv_thrown = (
        "Seq,ThrowOut,GiveFullCreditToAllETs,BonusItem,Item Text,Type,Original Answer,Adjusted Answer,Original Points,Adjusted Points\n"  # noqa: E501
        '40,True,False,False,Thrown Out,Choice,"x, y",,1,1\n'
    )
    qset_skip: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_thrown, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert "Q40" not in qset_skip.question_map

    qset_inc: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_thrown, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"include_thrown_out": True},
    )
    assert "Q40" in qset_inc.question_map
    assert isinstance(qset_inc.question_map["Q40"], ChoiceQuestion)

    # GiveFullCreditToAllETs rows (for rubric skip; question_set still includes as TEXT/CHOICE)
    # Provide a FITB with full credit; it should still parse into QuestionSet
    csv_fullcredit = (
        "Seq,ThrowOut,GiveFullCreditToAllETs,BonusItem,Item Text,Type,Original Answer,Adjusted Answer\n"  # noqa: E501
        '41,False,True,False,Full Credit FITB,Fill in the Blank,"{1} a",\n'
    )
    qset_fc: QuestionSet = load_question_set_via_adapter(
        StringSource(csv_fullcredit, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert "Q41" in qset_fc.question_map
    assert isinstance(qset_fc.question_map["Q41"], TextQuestion)


def test_examplify_question_set_builder_edges() -> None:
    adapter = ExamplifyQuestionSetAdapter()
    cfg = adapter.config

    default_question = adapter._build_question("essay", None, "", "", cfg, 2.0)
    assert isinstance(default_question, TextQuestion)
    assert default_question.max_points == 2.0

    empty_fitb = adapter._build_fitb_question(None, "", cfg, 3.0)
    assert isinstance(empty_fitb, TextQuestion)
    assert empty_fitb.max_points == 3.0
