from pathlib import Path

from gradeflow_engine.core import load_rubric_via_adapter
from gradeflow_engine.io.sources import FileSource, StringSource
from gradeflow_engine.rubrics.model import Rubric
from gradeflow_engine.rules.models.multi_valued import MultiValuedQuestionRule
from gradeflow_engine.rules.models.multiple_choice import MultipleChoiceQuestionRule
from gradeflow_engine.rules.models.number_equal import NumberEqualQuestionRule
from gradeflow_engine.rules.models.text_match import TextMatchQuestionRule, TextMatchRule


def test_choice_uses_adjusted_over_original_and_mode_defaults() -> None:
    # Adjusted Answer should override Original; default choice_mode is PARTIAL
    csv_text: str = (
        "Seq,ThrowOut,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points,"
        "GiveFullCreditToAllETs\n"
        '1,false,Choice,"x, y","a, b",2,1,false\n'
    )
    rubric: Rubric = load_rubric_via_adapter(
        StringSource(csv_text, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert len(rubric.rules) == 1
    r = rubric.rules[0]
    assert isinstance(r, MultipleChoiceQuestionRule)
    assert r.question_id == "Q1"
    # Default choice_mode after refactor is PARTIAL
    assert r.mode == "PARTIAL"
    # Answer should reflect adjusted ("a, b"), normalized and trimmed
    assert r.answer == {"a", "b"}


def test_fitb_single_and_multi_default_modes_and_points_floor_zero() -> None:
    # Single blank -> TextMatchQuestionRule (answers a|b)
    csv_single: str = (
        "Seq,ThrowOut,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points,"
        "GiveFullCreditToAllETs\n"
        '2,false,Fill in the Blank,"{1} a | b",,1,1,false\n'
    )
    rubric_single: Rubric = load_rubric_via_adapter(
        StringSource(csv_single, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert len(rubric_single.rules) == 1
    r2 = rubric_single.rules[0]
    assert isinstance(r2, TextMatchQuestionRule)
    assert r2.question_id == "Q2"
    assert set(r2.answers) == {"a", "b"}

    # Multi blank -> MultiValuedQuestionRule with inner TextMatchRules and
    # default aggregation PARTIAL
    csv_multi: str = (
        "Seq,ThrowOut,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points,"
        "GiveFullCreditToAllETs\n"
        '3,false,Fill in the Blank,"{1} a | b, {2} 1 | 2",,3,3,false\n'
    )
    rubric_multi: Rubric = load_rubric_via_adapter(
        StringSource(csv_multi, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert len(rubric_multi.rules) == 1
    r3 = rubric_multi.rules[0]
    assert isinstance(r3, MultiValuedQuestionRule)
    assert r3.question_id == "Q3"
    # Default multi_valued_mode is PARTIAL after refactor
    assert r3.aggregation == "PARTIAL"
    assert all(isinstance(rr, TextMatchRule) for rr in r3.rules)

    # Negative points -> floored at 0.0
    csv_neg: str = (
        "Seq,ThrowOut,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points,"
        "GiveFullCreditToAllETs\n"
        '4,false,Fill in the Blank,"{1} a",,-1,-1,false\n'
    )
    rubric_neg: Rubric = load_rubric_via_adapter(
        StringSource(csv_neg, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert len(rubric_neg.rules) == 1
    r4 = rubric_neg.rules[0]
    assert isinstance(r4, TextMatchQuestionRule)


def test_fitb_numeric_rules_when_parse_enabled_and_multi_valued_mode_override() -> None:
    # Enabling parse_answer_string switches numeric-like to NumberEqual rules;
    # override multi_valued_mode to ALL
    csv_multi_num: str = (
        "Seq,ThrowOut,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points,"
        "GiveFullCreditToAllETs\n"
        '5,false,Fill in the Blank,"{1} 10 | 20, {2} a | b",,2,2,false\n'
    )
    rubric_mv_num: Rubric = load_rubric_via_adapter(
        StringSource(csv_multi_num, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"parse_answer_string": True, "multi_valued_mode": "ALL"},
    )
    assert len(rubric_mv_num.rules) == 1
    r5 = rubric_mv_num.rules[0]
    assert isinstance(r5, MultiValuedQuestionRule)
    assert r5.question_id == "Q5"
    assert r5.aggregation == "ALL"
    # First position numeric → NumberEqualRule; second position text → TextMatchRule
    assert r5.rules[0].type == "NUMBER_EQUAL"
    assert r5.rules[1].type == "TEXT_MATCH"


def test_skip_give_full_credit_rows_and_include_thrown_out_via_config() -> None:
    # GiveFullCreditToAllETs=true -> skip
    csv_skip: str = (
        "Seq,ThrowOut,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points,"
        "GiveFullCreditToAllETs\n"
        '6,false,Choice,"x, y",,2,2,true\n'
    )
    rubric_skip: Rubric = load_rubric_via_adapter(
        StringSource(csv_skip, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert len(rubric_skip.rules) == 0

    # Thrown-out row: default is exclude; include with config
    csv_thrown: str = (
        "Seq,ThrowOut,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points,"
        "GiveFullCreditToAllETs\n"
        '7,true,Choice,"a, b",,1,1,false\n'
    )
    rubric_inc: Rubric = load_rubric_via_adapter(
        StringSource(csv_thrown, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"include_thrown_out": True},
    )
    assert len(rubric_inc.rules) == 1
    r7 = rubric_inc.rules[0]
    assert isinstance(r7, MultipleChoiceQuestionRule)
    assert r7.question_id == "Q7"
    assert r7.answer == {"a", "b"}


def _example_csv_path() -> Path:
    tests_dir = Path(__file__).resolve().parent.parent.parent
    return tests_dir / "data" / "Adjust_Scoring.csv"


def test_rubric_from_full_csv_defaults_modes_and_answers() -> None:
    """
    Default: parse_answer_string=False; choice_mode=PARTIAL; multi_valued_mode=PARTIAL
    - Choice rules use normalized answers; mode PARTIAL; points from Adjusted/Original
    - FITB single default TextMatchQuestionRule
    - FITB multi default MultiValuedQuestionRule of TextMatch inner rules with PARTIAL aggregation
    """
    csv_path = _example_csv_path()
    rubric: Rubric = load_rubric_via_adapter(
        FileSource(csv_path),
        adapter_name="examplify",
    )
    rules = {
        r.question_id: r
        for r in rubric.rules
        if isinstance(
            r, (MultipleChoiceQuestionRule, TextMatchQuestionRule, MultiValuedQuestionRule)
        )
    }

    # Choice rules: normalized answers; default mode PARTIAL; points from Adjusted/Original
    r1 = rules["Q1"]
    assert isinstance(r1, MultipleChoiceQuestionRule)
    assert r1.mode == "PARTIAL"
    assert r1.answer == {"b", "c", "f", "g"}

    r2 = rules["Q2"]
    assert isinstance(r2, MultipleChoiceQuestionRule)
    assert r2.answer == {"a"}

    r3 = rules["Q3"]
    assert isinstance(r3, MultipleChoiceQuestionRule)
    assert r3.answer == {"a", "c", "d"}

    r4 = rules["Q4"]
    assert isinstance(r4, MultipleChoiceQuestionRule)
    # Prefer Adjusted Answer for rule (A, B, C, E)
    assert r4.answer == {"a", "b", "c", "e"}

    r5 = rules["Q5"]
    assert isinstance(r5, MultipleChoiceQuestionRule)
    assert r5.answer == {"a", "c", "d", "e"}

    # FITB defaults (PARTIAL aggregation)
    r6 = rules["Q6"]
    assert isinstance(r6, MultiValuedQuestionRule)
    assert r6.aggregation == "PARTIAL"
    assert all(isinstance(inner, TextMatchRule) for inner in r6.rules)

    r7 = rules["Q7"]
    assert isinstance(r7, TextMatchQuestionRule)
    # variations of 'e^-1' present among acceptable answers
    assert any("e" in a for a in r7.answers)

    r8 = rules["Q8"]
    assert isinstance(r8, MultiValuedQuestionRule)
    assert r8.aggregation == "PARTIAL"
    assert all(isinstance(inner, TextMatchRule) for inner in r8.rules)

    r11 = rules["Q11"]
    assert isinstance(r11, MultiValuedQuestionRule)
    assert r11.aggregation == "PARTIAL"
    assert all(isinstance(inner, TextMatchRule) for inner in r11.rules)

    r13 = rules["Q13"]
    assert isinstance(r13, TextMatchQuestionRule)
    assert set(r13.answers) >= {"0.1", "0.10", "0.098"}

    r14 = rules["Q14"]
    assert isinstance(r14, TextMatchQuestionRule)


def test_rubric_from_full_csv_parse_enabled_numeric_and_aggregation_override() -> None:
    """
    Enable numeric parsing and override multi_valued_mode to ALL:
    - Q6/Q8/Q22: numeric-like -> NumberEqualRule inner rules; aggregation ALL
    - Q7: textual single blank remains TextMatchQuestionRule
    - Q13/Q18/Q19/Q23/Q24: numeric-like single blank -> NumberEqualQuestionRule
    """
    csv_path = _example_csv_path()
    rubric: Rubric = load_rubric_via_adapter(
        FileSource(csv_path),
        adapter_name="examplify",
        adapter_kwargs={"parse_answer_string": True, "multi_valued_mode": "ALL"},
    )
    rules = {
        r.question_id: r
        for r in rubric.rules
        if isinstance(
            r,
            (TextMatchQuestionRule, MultiValuedQuestionRule, NumberEqualQuestionRule),
        )
    }

    r6 = rules["Q6"]
    assert isinstance(r6, MultiValuedQuestionRule)
    assert r6.aggregation == "ALL"
    assert r6.rules[0].type == "NUMBER_EQUAL"
    assert r6.rules[1].type == "NUMBER_EQUAL"

    r8 = rules["Q8"]
    assert isinstance(r8, MultiValuedQuestionRule)
    assert r8.aggregation == "ALL"
    assert r8.rules[0].type == "NUMBER_EQUAL"
    assert r8.rules[1].type == "NUMBER_EQUAL"

    r22 = rules["Q22"]
    assert isinstance(r22, MultiValuedQuestionRule)
    assert r22.aggregation == "ALL"
    assert r22.rules[0].type == "NUMBER_EQUAL"
    assert r22.rules[1].type == "NUMBER_EQUAL"

    r7 = rules["Q7"]
    assert isinstance(r7, TextMatchQuestionRule)

    # Verify numeric single-blank rules are the right type
    for qid in ["Q13", "Q18", "Q19", "Q23", "Q24"]:
        rule = rules[qid]
        assert isinstance(rule, NumberEqualQuestionRule)


def test_rubric_include_thrown_out_and_skip_full_credit() -> None:
    """
    Additional coverage for include_thrown_out=True and GiveFullCreditToAllETs=True.
    These cases are not present in the full CSV; exercise them via inline data:
    - Thrown-out row: excluded by default; included when configured.
    - GiveFullCreditToAllETs row: skipped (no rule emitted).
    """
    # Thrown-out row: excluded by default
    csv_thrown = (
        "Seq,ThrowOut,GiveFullCreditToAllETs,BonusItem,Item Text,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points\n"  # noqa: E501
        '40,True,False,False,Thrown Out,Choice,"x, y",,2,1\n'
    )
    rubric_skip: Rubric = load_rubric_via_adapter(
        StringSource(csv_thrown, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert len(rubric_skip.rules) == 0

    # Include thrown-out via config
    rubric_inc: Rubric = load_rubric_via_adapter(
        StringSource(csv_thrown, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
        adapter_kwargs={"include_thrown_out": True},
    )
    assert len(rubric_inc.rules) == 1
    r = rubric_inc.rules[0]
    assert isinstance(r, MultipleChoiceQuestionRule)
    assert r.question_id == "Q40"
    assert r.answer == {"x", "y"}

    # GiveFullCreditToAllETs row: skipped (no rule emitted)
    csv_fullcredit = (
        "Seq,ThrowOut,GiveFullCreditToAllETs,BonusItem,Item Text,Type,Original Answer,Adjusted Answer,Adjusted Points,Original Points\n"  # noqa: E501
        '41,False,True,False,Full Credit Choice,Choice,"a, b",,2,2\n'
    )
    rubric_fc: Rubric = load_rubric_via_adapter(
        StringSource(csv_fullcredit, media_type="text/csv", extension="csv"),
        adapter_name="examplify",
    )
    assert len(rubric_fc.rules) == 0
