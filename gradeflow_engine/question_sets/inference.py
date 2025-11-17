from ..questions.models import Question
from ..questions.models.choice import ChoiceQuestion
from ..questions.models.multi_valued import MultiValuedQuestion
from ..questions.models.numeric import NumericQuestion
from ..questions.models.text import TextQuestion
from ..questions.parser import MultiValuedParserConfig
from ..questions.types import QuestionId
from ..questions.utils import parse_multi_value, try_parse_number
from ..submissions.models import RawSubmission

DEFAULT_CHOICE_DELIMITER = ","
DEFAULT_MULTI_VALUE_DELIMITER = "|"
DEFAULT_CHOICE_OPTION_LIMIT = 5


def _get_question_ids(raw_submissions: list[RawSubmission]) -> set[QuestionId]:
    return {qid for rs in raw_submissions for qid in rs.raw_answer_map.keys()}


def _get_raw_answers_for_qid(raw_submissions: list[RawSubmission], qid: QuestionId) -> list[str]:
    return [rs.raw_answer_map[qid] for rs in raw_submissions if qid in rs.raw_answer_map]


def _tokenize_with_config(raw: str, config: MultiValuedParserConfig) -> list[str]:
    return parse_multi_value(
        raw,
        delimiter=config.delimiter,
        normalize_case=config.normalize_case,
        trim_whitespace=config.trim_whitespace,
    )


def _get_multi_value_cardinalities(
    raw_answers: list[str], config: MultiValuedParserConfig
) -> set[int]:
    counts: set[int] = set()
    for raw in raw_answers:
        if not raw:  # ignore empty raw strings
            continue
        tokens = _tokenize_with_config(raw, config)
        counts.add(len(tokens))
    return counts


def _get_numeric_answers(raw_answers: list[str]) -> list[float]:
    numeric_answers: list[float] = []
    for raw in raw_answers:
        if not raw:
            continue
        try:
            num = try_parse_number(raw.strip())
            numeric_answers.append(num)
        except ValueError:
            continue
    return numeric_answers


def _get_observed_values(raw_answers: list[str], config: MultiValuedParserConfig) -> set[str]:
    values: set[str] = set()
    for raw in raw_answers:
        if not raw:
            continue
        for t in _tokenize_with_config(raw, config):
            if not t:
                continue  # ignore empty tokens
            values.add(t)
    return values


def _infer_question_for_qid(
    raw_answers: list[str],
    choice_delimiter: str,
    choice_option_limit: int,
    multi_value_delimiter: str,
) -> Question:
    """
    Inference order:
    1) MultiValued: all non-empty submissions split to the same cardinality > 1
    2) Numeric: majority of answers are numeric
    3) Choice: limited distinct values
    4) Text
    """
    if not raw_answers:
        return TextQuestion()

    # Build configs that mirror how the questions will parse
    choice_config = MultiValuedParserConfig(delimiter=choice_delimiter)
    multi_value_config = MultiValuedParserConfig(delimiter=multi_value_delimiter)

    # Precompute observed values and counts for Choice using its config
    observed_values = _get_observed_values(raw_answers, config=choice_config)
    choice_counts = _get_multi_value_cardinalities(raw_answers, config=choice_config)

    # 1) Multi-valued requires consistent cardinality across submissions and > 1
    multi_value_counts = _get_multi_value_cardinalities(raw_answers, config=multi_value_config)
    if len(multi_value_counts) == 1 and next(iter(multi_value_counts)) > 1:
        return MultiValuedQuestion(config=multi_value_config)

    # 2) Numeric majority
    elif len(_get_numeric_answers(raw_answers)) > len(raw_answers) / 2:
        return NumericQuestion()

    # 3) Choice: limited distinct values
    elif 0 < len(observed_values) <= choice_option_limit:
        return ChoiceQuestion(
            options=observed_values,
            allow_multiple=choice_counts != {1},  # allow multiple if not all single-token
            config=choice_config,
        )

    # 4) Fallback
    else:
        return TextQuestion()


def infer_question_map(
    raw_submissions: list[RawSubmission],
    choice_delimiter: str,
    choice_option_limit: int,
    multi_value_delimiter: str,
) -> dict[QuestionId, Question]:
    question_map: dict[QuestionId, Question] = {}
    for qid in _get_question_ids(raw_submissions):
        raw_answers = _get_raw_answers_for_qid(raw_submissions, qid)
        question_map[qid] = _infer_question_for_qid(
            raw_answers,
            choice_delimiter=choice_delimiter,
            choice_option_limit=choice_option_limit,
            multi_value_delimiter=multi_value_delimiter,
        )
    return question_map
