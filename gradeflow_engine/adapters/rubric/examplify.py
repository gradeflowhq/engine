from typing import Literal

from pydantic import ValidationError

from ...exceptions import AdapterLoadError, GradeFlowError, RubricValidationError
from ...io.sources import DataSource
from ...questions.models.choice import ChoiceQuestion
from ...questions.parser import MultiValuedParserConfig
from ...rubrics.model import Rubric
from ...rules.models import QuestionRule, SingleTargetQuestionRule, SingleTargetRule
from ...rules.models.multi_valued import MultiValuedQuestionRule
from ...rules.models.multiple_choice import MultipleChoiceQuestionRule
from ...rules.models.number_equal import NumberEqualQuestionRule, NumberEqualRule
from ...rules.models.text_match import TextMatchQuestionRule, TextMatchRule
from ..common.examplify import (
    CHOICE_DELIMITER,
    CHOICE_NORMALIZE_CASE,
    TRIM_WHITESPACE,
    ExamplifyRuleConfig,
    build_qid,
    extract_blank_segments,
    get_str,
    is_all_numeric_str,
    make_dict_reader,
    parse_number_str_list,
    split_alternatives,
)
from ..registries import RubricAdapter, rubric_adapter_registry


class ExamplifyRubricAdapter(RubricAdapter):
    """
    Examplify → Rubric adapter with separate RuleConfig.

    Behavior:
    - Prefer "Adjusted Answer" over "Original Answer" for the answer key.
    - Skip rows with GiveFullCreditToAllETs == true.
    - Respect include_thrown_out: False by default (skip thrown-out rows unless enabled).
    - For Choice questions:
        * Parse the answer key using constants (delimiter, normalization, trimming).
        * Produce MultipleChoiceQuestionRule with mode from cfg.choice_mode.
    - For Fill in the Blank:
        * Format: "{1} VAL1, {2} VAL2, ..." where VAL may be "A|B|...".
        * If parse_answer_string is True:
            - Single blank numeric-like → NumberEqualQuestionRule (answers parsed to numbers)
            - Multi-blank: per-position numeric-like → NumberEqualRule, else TextMatchRule
            - Aggregation for multi-blank rules uses cfg.multi_valued_mode
          Else:
            - Single blank → TextMatchQuestionRule (string answers)
            - Multi-blank → MultiValuedQuestionRule of TextMatchRule(s) with cfg.multi_valued_mode
    - Points: use Adjusted Points or Original Points; floor at 0.0 when missing/negative.
    """

    name: Literal["examplify"] = "examplify"
    config: ExamplifyRuleConfig = ExamplifyRuleConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def load(self, source: DataSource) -> Rubric:
        try:
            return self._load(source)
        except ValidationError as e:
            raise RubricValidationError(e) from e
        except GradeFlowError:
            raise
        except Exception as e:
            raise AdapterLoadError(self.name, str(e)) from e

    def _load(self, source: DataSource) -> Rubric:
        cfg = self.config
        rules: list[QuestionRule] = []

        for row in make_dict_reader(source.read().data.decode("utf-8")):
            qid = self._maybe_build_qid(row, cfg)
            if not qid:
                continue

            qtype = get_str(row, "Type").lower()
            source_answer = self._preferred_answer_key(row)
            if self._skip_row(row, cfg, source_answer):
                continue

            rule: SingleTargetQuestionRule | None
            if qtype == "choice":
                rule = self._build_choice_rule(qid, source_answer, cfg)
            elif qtype == "fill in the blank":
                rule = self._build_fitb_rule(qid, source_answer, cfg)
            else:
                # Default to exact match on the literal answer string
                rule = self._build_text_match_rule(qid, [source_answer])

            if rule is not None:
                rules.append(rule)

        return Rubric(rules=rules)

    # -----------------
    # Helpers
    # -----------------
    def _maybe_build_qid(self, row: dict[str, str | None], cfg: ExamplifyRuleConfig) -> str | None:
        seq = get_str(row, "Seq")
        if not seq:
            return None
        if not cfg.include_thrown_out and get_str(row, "ThrowOut").lower() == "true":
            return None
        return build_qid(cfg, seq)

    def _preferred_answer_key(self, row: dict[str, str | None]) -> str:
        adjusted = get_str(row, "Adjusted Answer")
        original = get_str(row, "Original Answer")
        return adjusted or original

    def _skip_row(self, row: dict[str, str | None], cfg: ExamplifyRuleConfig, source: str) -> bool:
        if get_str(row, "GiveFullCreditToAllETs").lower() == "true":
            return True
        return not bool(source)

    # -----------------
    # Builders
    # -----------------
    def _build_choice_rule(
        self, qid: str, source: str, cfg: ExamplifyRuleConfig
    ) -> MultipleChoiceQuestionRule | None:
        # Parse using the same configuration constants the QuestionSet uses
        choice_cfg = MultiValuedParserConfig(
            delimiter=CHOICE_DELIMITER,
            normalize_case=CHOICE_NORMALIZE_CASE,
            trim_whitespace=TRIM_WHITESPACE,
        )
        parsed = ChoiceQuestion(config=choice_cfg).parse(source)
        answer_set = {t for t in parsed if t}
        if not answer_set:
            return None
        return MultipleChoiceQuestionRule(
            question_id=qid,
            answer=answer_set,
            mode=cfg.choice_mode,
        )

    def _build_fitb_rule(
        self, qid: str, source: str, cfg: ExamplifyRuleConfig
    ) -> SingleTargetQuestionRule | None:
        # Multi-value FITB format: "{1} VAL1, {2} VAL2, ..." where VAL may be "A|B|..."
        segments = extract_blank_segments(source) or [source]
        alt_lists = [
            split_alternatives(seg, skip_empty=cfg.skip_empty_alternatives) for seg in segments
        ]

        # Single blank
        if len(alt_lists) <= 1:
            alts = alt_lists[0] if alt_lists else []
            if not alts:
                return None

            if cfg.parse_answer_string and is_all_numeric_str(alts):
                # Use numeric equality; parse strings to numbers
                parsed_numbers = parse_number_str_list(alts)
                return NumberEqualQuestionRule(
                    question_id=qid,
                    answers=parsed_numbers,
                )

            # Default to exact string match
            return TextMatchQuestionRule(
                question_id=qid,
                answers=alts,
            )

        # Multiple blanks: build inner rules per position
        inner_rules: list[SingleTargetRule] = []
        for alts in alt_lists:
            if not alts:
                return None
            if cfg.parse_answer_string and is_all_numeric_str(alts):
                parsed_numbers = parse_number_str_list(alts)
                inner_rules.append(NumberEqualRule(answers=parsed_numbers))
            else:
                inner_rules.append(TextMatchRule(answers=alts))

        return MultiValuedQuestionRule(
            question_id=qid,
            rules=inner_rules,
            aggregation=cfg.multi_valued_mode,
        )

    def _build_text_match_rule(self, qid: str, answers: list[str]) -> TextMatchQuestionRule | None:
        if not answers:
            return None
        return TextMatchQuestionRule(
            question_id=qid,
            answers=answers,
        )


# Canonical registration
rubric_adapter_registry.register("examplify", ExamplifyRubricAdapter)  # type: ignore[arg-type]
