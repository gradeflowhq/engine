import csv
from collections.abc import Iterable
from io import StringIO
from typing import Literal

from natsort import natsorted
from pydantic import BaseModel, Field

from ...questions.types import Answer
from ...rules.result import QuestionResult
from ...submissions.models import Submission
from ..base import DataBlob, Serializer
from ..registries import submissions_serializer_registry

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class CsvSubmissionsConfig(BaseModel):
    format: Literal["csv"] = "csv"
    student_id_column: str = Field(default="student_id")
    include_answers: bool = Field(default=True)
    include_per_question_results: bool = Field(default=True)
    include_feedback: bool = Field(default=True)
    include_total: bool = Field(default=True)
    include_remarks: bool = Field(default=True)
    include_rounded_total: bool = Field(default=True)
    rounding_base: float = Field(default=0.5)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RESULT_SUFFIXES: tuple[str, ...] = ("__points", "__max_points", "__passed", "__percent")


# ---------------------------------------------------------------------------
# Answer serialization
# ---------------------------------------------------------------------------


def _serialize_answer(answer: Answer) -> str:
    if isinstance(answer, set):
        return "; ".join(natsorted(map(str, answer)))
    if isinstance(answer, list):
        return " | ".join(map(str, answer))
    return str(answer)


# ---------------------------------------------------------------------------
# Rounding helpers
# ---------------------------------------------------------------------------


def _round_nearest(value: float, base: float) -> float:
    return round(value / base) * base


def _maybe_round(value: float, rounding_base: float) -> float:
    if rounding_base > 0:
        return _round_nearest(value, rounding_base)
    return value


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _percent(points: float, max_points: float) -> float:
    return 0.0 if max_points == 0 else points / max_points * 100


# ---------------------------------------------------------------------------
# Totals computation
# ---------------------------------------------------------------------------


def _compute_totals(
    result_map: dict[str, QuestionResult],
    ordered_qids: list[str],
    rounding_base: float,
) -> dict[str, float]:
    """
    Compute earned points, maximum points, and derived values for one submission.
    """
    earned = sum(result_map[qid].points for qid in ordered_qids if qid in result_map)
    maximum = sum(result_map[qid].max_points for qid in ordered_qids if qid in result_map)
    pct = _percent(earned, maximum)
    return {
        "total_points": earned,
        "total_max_points": maximum,
        "total_percent": pct,
        "rounded_total_points": _maybe_round(earned, rounding_base),
        "rounded_total_max_points": _maybe_round(maximum, rounding_base),
        "rounded_total_percent": _maybe_round(pct, rounding_base),
    }


# ---------------------------------------------------------------------------
# Remarks
# ---------------------------------------------------------------------------


def _question_remarks(qid: str, result: QuestionResult) -> str:
    percent = int(result.points / result.max_points * 100) if result.max_points > 0 else 0
    remarks = f"[[{qid}]] {result.points}/{result.max_points} points | {percent}%"
    if result.feedback.strip() != "":
        remarks += f"\n\n{result.feedback}\n"
    return remarks


def _build_remarks(
    result_map: dict[str, QuestionResult],
    ordered_qids: list[str],
    totals: dict[str, float],
    *,
    include_rounded_total: bool,
) -> str:
    per_question = "\n\n".join(
        _question_remarks(qid, result_map[qid]) for qid in ordered_qids if qid in result_map
    )

    summary = f"\n\n---\n\nTotal: {totals['total_points']}/{totals['total_max_points']} points"
    if include_rounded_total:
        summary += (
            f"\nRounded Total: {totals['rounded_total_points']}/"
            f"{totals['rounded_total_max_points']} points"
        )
    summary += f"\n\nPercentage: {totals['total_percent']}%"
    if include_rounded_total:
        summary += f"\nRounded Percentage: {totals['rounded_total_percent']}%"

    return per_question + summary


# ---------------------------------------------------------------------------
# Field-name generation
# ---------------------------------------------------------------------------


def _question_result_columns(qid: str) -> list[str]:
    return [f"{qid}{s}" for s in _RESULT_SUFFIXES]


def _generate_fieldnames(
    student_id_column: str,
    ordered_qids: list[str],
    *,
    include_answers: bool,
    include_per_question_results: bool,
    include_feedback: bool,
    include_remarks: bool,
    include_total: bool,
    include_rounded_total: bool,
) -> list[str]:
    fields: list[str] = [student_id_column]
    if include_answers:
        fields.extend(ordered_qids)
    if include_per_question_results:
        for qid in ordered_qids:
            fields.extend(_question_result_columns(qid))
    if include_feedback:
        fields.extend(f"{qid}__feedback" for qid in ordered_qids)
    if include_remarks:
        fields.append("remarks")
    if include_total:
        fields.extend(["total_points", "total_max_points", "total_percent"])
    if include_rounded_total:
        fields.extend(["rounded_total_points", "rounded_total_max_points", "rounded_total_percent"])
    return fields


# ---------------------------------------------------------------------------
# Per-question result columns
# ---------------------------------------------------------------------------


def _result_columns_for_qid(qid: str, res: QuestionResult | None) -> dict[str, str]:
    """
    Return the four per-question result columns for a single question ID.
    All values are empty strings when there is no result for that question.
    """
    if res is None:
        return dict.fromkeys(_question_result_columns(qid), "")
    pct = _percent(res.points, res.max_points)
    return {
        f"{qid}__points": str(res.points),
        f"{qid}__max_points": str(res.max_points),
        f"{qid}__passed": "TRUE" if res.passed else "FALSE",
        f"{qid}__percent": str(pct) if res.max_points > 0 else "N/A",
    }


# ---------------------------------------------------------------------------
# Question IDs discovery
# ---------------------------------------------------------------------------


def _collect_question_ids(submissions: list[Submission]) -> list[str]:
    qids: set[str] = set()
    for s in submissions:
        qids.update(s.answer_map.keys())
        qids.update(s.result_map.keys())
    return natsorted(qids)


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------


def _create_row(
    gs: Submission,
    ordered_qids: list[str],
    *,
    config: CsvSubmissionsConfig,
) -> dict[str, str]:
    row: dict[str, str] = {config.student_id_column: gs.student_id}
    result_map = gs.result_map
    totals = _compute_totals(result_map, ordered_qids, config.rounding_base)

    if config.include_answers:
        for qid in ordered_qids:
            row[qid] = _serialize_answer(gs.answer_map.get(qid, ""))

    if config.include_per_question_results:
        for qid in ordered_qids:
            row.update(_result_columns_for_qid(qid, result_map.get(qid)))

    if config.include_feedback:
        for qid in ordered_qids:
            res = result_map.get(qid)
            row[f"{qid}__feedback"] = (res.feedback or "") if res else ""

    if config.include_remarks:
        row["remarks"] = _build_remarks(
            result_map,
            ordered_qids,
            totals,
            include_rounded_total=config.include_rounded_total,
        )

    if config.include_total:
        row["total_points"] = str(totals["total_points"])
        row["total_max_points"] = str(totals["total_max_points"])
        row["total_percent"] = str(totals["total_percent"])

    if config.include_rounded_total:
        row["rounded_total_points"] = str(totals["rounded_total_points"])
        row["rounded_total_max_points"] = str(totals["rounded_total_max_points"])
        row["rounded_total_percent"] = str(totals["rounded_total_percent"])

    return row


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


class CsvSubmissionsSerializer(Serializer[Iterable[Submission]]):
    format = "csv"
    media_type = "text/csv"
    config: CsvSubmissionsConfig = CsvSubmissionsConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def dumps(self, submissions: Iterable[Submission]) -> DataBlob:
        subs = list(submissions)
        ordered_qids = _collect_question_ids(subs)
        fieldnames = _generate_fieldnames(
            self.config.student_id_column,
            ordered_qids,
            include_answers=self.config.include_answers,
            include_per_question_results=self.config.include_per_question_results,
            include_feedback=self.config.include_feedback,
            include_remarks=self.config.include_remarks,
            include_total=self.config.include_total,
            include_rounded_total=self.config.include_rounded_total,
        )
        out = StringIO()
        writer = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        rows = [
            _create_row(
                gs,
                ordered_qids,
                config=self.config,
            )
            for gs in subs
        ]
        rows = natsorted(rows, key=lambda r: r[self.config.student_id_column])
        for row in rows:
            writer.writerow(row)
        return DataBlob(
            data=out.getvalue().encode("utf-8"), media_type=self.media_type, extension="csv"
        )

    def loads(self, blob: DataBlob) -> Iterable[Submission]:
        raise NotImplementedError("Deserializing graded submissions from CSV is not supported.")


submissions_serializer_registry.register("csv", CsvSubmissionsSerializer)
