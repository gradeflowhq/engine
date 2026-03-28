from typing import Literal

from ...io.sources import DataSource
from ...question_sets.model import QuestionSet
from ...questions.models import ChoiceQuestion, NumericQuestion, Question, TextQuestion
from ...questions.models.multi_valued import MultiValuedQuestion, MultiValueTypes
from ...questions.parser import BaseParserConfig, MultiValuedParserConfig, TextParserConfig
from ...questions.utils import parse_multi_value
from ..common.examplify import (
    CHOICE_DELIMITER,
    CHOICE_NORMALIZE_CASE,
    EMPTY_MARKER,
    MULTI_VALUE_DELIMITER,
    TRIM_WHITESPACE,
    ExamplifyParseConfig,
    build_qid,
    extract_blank_segments,
    get_str,
    is_all_numeric_str,
    make_dict_reader,
    points_from_row,
    split_alternatives,
)
from ..registries import QuestionSetAdapter, question_set_adapter_registry


class ExamplifyQuestionSetAdapter(QuestionSetAdapter):
    name: Literal["examplify"] = "examplify"
    config: ExamplifyParseConfig = ExamplifyParseConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def load(self, source: DataSource) -> QuestionSet:
        cfg = self.config
        qmap: dict[str, Question] = {}

        for row in make_dict_reader(source.read().data.decode("utf-8")):
            qid = self._maybe_build_qid(row, cfg)
            if not qid:
                continue

            qtype = get_str(row, "Type").lower()
            description = self._desc(row)
            original_ans, adjusted_ans = self._answers(row)

            max_points = points_from_row(row)
            qmap[qid] = self._build_question(
                qtype, description, original_ans, adjusted_ans, cfg, max_points
            )

        return QuestionSet(question_map=qmap)

    # --------- helpers ---------
    def _maybe_build_qid(self, row: dict[str, str | None], cfg: ExamplifyParseConfig) -> str | None:
        seq = get_str(row, "Seq")
        if not seq:
            return None
        if not cfg.include_thrown_out and get_str(row, "ThrowOut").lower() == "true":
            return None
        return build_qid(cfg, seq)

    def _desc(self, row: dict[str, str | None]) -> str | None:
        s = get_str(row, "Item Text")
        return s or None

    def _answers(self, row: dict[str, str | None]) -> tuple[str, str]:
        return get_str(row, "Original Answer"), get_str(row, "Adjusted Answer")

    # --------- builders ---------
    def _build_question(
        self,
        qtype: str,
        description: str | None,
        original_ans: str,
        adjusted_ans: str,
        cfg: ExamplifyParseConfig,
        max_points: float,
    ) -> Question:
        if qtype == "choice":
            return self._build_choice_question(description, original_ans, adjusted_ans, max_points)
        if qtype == "fill in the blank":
            return self._build_fitb_question(
                description, adjusted_ans or original_ans, cfg, max_points
            )
        return TextQuestion(description=description, max_points=max_points)

    def _build_choice_question(
        self,
        description: str | None,
        original_ans: str,
        adjusted_ans: str,
        max_points: float,
    ) -> ChoiceQuestion:
        opts: set[str] = set()
        for src in (original_ans, adjusted_ans):
            if not src:
                continue
            tokens = parse_multi_value(
                src,
                delimiter=CHOICE_DELIMITER,
                normalize_case=CHOICE_NORMALIZE_CASE,
                trim_whitespace=TRIM_WHITESPACE,
            )
            opts.update(t for t in tokens if t)

        # Autodetect allow_multiple
        allow_multiple = any(
            len(
                parse_multi_value(
                    src,
                    delimiter=CHOICE_DELIMITER,
                    normalize_case=CHOICE_NORMALIZE_CASE,
                    trim_whitespace=TRIM_WHITESPACE,
                )
            )
            > 1
            for src in (original_ans, adjusted_ans)
            if src
        )

        choice_cfg = MultiValuedParserConfig(
            delimiter=CHOICE_DELIMITER,
            normalize_case=CHOICE_NORMALIZE_CASE,
            trim_whitespace=TRIM_WHITESPACE,
        )
        return ChoiceQuestion(
            description=description,
            config=choice_cfg,
            options=opts,
            allow_multiple=allow_multiple,
            max_points=max_points,
        )

    def _build_fitb_question(
        self,
        description: str | None,
        source: str | None,
        cfg: ExamplifyParseConfig,
        max_points: float,
    ) -> TextQuestion | NumericQuestion | MultiValuedQuestion:
        if not source:
            return TextQuestion(description=description, max_points=max_points)

        # Multi-value FITB format: "{1} VAL1, {2} VAL2, ..." where VAL may be "A|B|..."
        segments = extract_blank_segments(source) or [source]
        alt_lists = [
            split_alternatives(seg, skip_empty=cfg.skip_empty_alternatives) for seg in segments
        ]

        # Single blank
        if len(alt_lists) <= 1:
            alts = alt_lists[0] if alt_lists else []
            if cfg.parse_answer_string and is_all_numeric_str(alts):
                return NumericQuestion(
                    description=description,
                    config=BaseParserConfig(empty_marker=EMPTY_MARKER),
                    max_points=max_points,
                )
            return TextQuestion(
                description=description,
                config=TextParserConfig(
                    empty_marker=EMPTY_MARKER,
                    trim_whitespace=TRIM_WHITESPACE,
                    normalize_case=False,
                ),
                max_points=max_points,
            )

        # Multiple blanks
        value_types: list[MultiValueTypes] = (
            ["NUMERIC" if is_all_numeric_str(alts) else "TEXT" for alts in alt_lists]
            if cfg.parse_answer_string
            else ["TEXT"] * len(alt_lists)
        )

        mv_cfg = MultiValuedParserConfig(
            delimiter=MULTI_VALUE_DELIMITER,
            normalize_case=False,
            trim_whitespace=TRIM_WHITESPACE,
            empty_marker=EMPTY_MARKER,
        )
        return MultiValuedQuestion(
            description=description,
            config=mv_cfg,
            value_types=value_types,
            max_points=max_points,
        )


question_set_adapter_registry.register("examplify", ExamplifyQuestionSetAdapter)  # type: ignore[arg-type]
