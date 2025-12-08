import csv
from collections.abc import Iterable
from io import StringIO
from typing import Literal

from natsort import natsorted
from pydantic import BaseModel, Field

from ...questions.types import Answer
from ...rules.result import QuestionResult
from ...submissions.models import GradedSubmission
from ..base import DataBlob, Serializer
from ..registries import graded_submissions_serializer_registry


class CsvGradedSubmissionsConfig(BaseModel):
    format: Literal["csv"] = "csv"
    student_id_column: str = Field(default="student_id")
    include_answers: bool = Field(default=True)
    include_per_question_results: bool = Field(default=True)
    include_feedback: bool = Field(default=True)
    include_total: bool = Field(default=True)
    include_remarks: bool = Field(default=True)
    include_rounded_total: bool = Field(default=True)
    rounding_base: float = Field(default=0.5)


def _serialize_answer(answer: Answer) -> str:
    if isinstance(answer, set):
        return "; ".join(sorted(map(str, answer)))
    if isinstance(answer, list):
        return " | ".join(map(str, answer))
    return str(answer)


def _round_nearest(value: float, base: float) -> float:
    return round(value / base) * base


def _maybe_round(value: float, rounding_base: float) -> float:
    if rounding_base > 0:
        return _round_nearest(value, rounding_base)
    return value


def _get_total_points(results: list[QuestionResult], rounding_base: float) -> float:
    return sum(result.points for result in results)


def _get_total_max_points(results: list[QuestionResult], rounding_base: float) -> float:
    return sum(result.max_points for result in results)


def _get_total_percent(results: list[QuestionResult], rounding_base: float) -> float:
    total_max = _get_total_max_points(results, rounding_base=rounding_base)
    if total_max == 0:
        return 0.0
    return _get_total_points(results, rounding_base=rounding_base) / total_max * 100


def _question_remarks(result: QuestionResult) -> str:
    percent = int(result.points / result.max_points * 100) if result.max_points > 0 else 0.0
    return f"""[[{result.question_id}]] {result.points}/{result.max_points} points | {percent}%

{result.feedback}
"""


def _remarks(
    results: list[QuestionResult],
    total_points: float,
    total_max_points: float,
    total_percent: float,
) -> str:
    return (
        "\n\n".join(_question_remarks(res) for res in results)
        + f"""
---

Total: {total_points}/{total_max_points} points | {total_percent}%
"""
    )


def _collect_question_ids(submissions: list[GradedSubmission]) -> list[str]:
    qids: set[str] = set()
    for gs in submissions:
        qids.update(gs.answer_map.keys())
        qids.update(res.question_id for res in gs.results)
    return natsorted(qids)


def _generate_question_result_columns(qid: str) -> list[str]:
    return [f"{qid}__points", f"{qid}__max_points", f"{qid}__passed", f"{qid}__percent"]


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
            fields.extend(_generate_question_result_columns(qid))
    if include_feedback:
        fields.extend(f"{qid}__feedback" for qid in ordered_qids)
    if include_remarks:
        fields.append("remarks")
    if include_total:
        fields.extend(["total_points", "total_max_points", "total_percent"])
    if include_rounded_total:
        fields.extend(["rounded_total_points", "rounded_total_max_points", "rounded_total_percent"])
    return fields


def _build_result_lookup(
    results: list[QuestionResult], ordered_qids: list[str]
) -> tuple[dict[str, QuestionResult], list[QuestionResult]]:
    result_by_qid = {res.question_id: res for res in results}
    ordered = [result_by_qid[qid] for qid in ordered_qids if qid in result_by_qid]
    return result_by_qid, ordered


def _create_row(
    gs: GradedSubmission,
    ordered_qids: list[str],
    *,
    config: CsvGradedSubmissionsConfig,
) -> dict[str, str]:
    row: dict[str, str] = {config.student_id_column: gs.student_id}
    result_by_qid, ordered_results = _build_result_lookup(gs.results, ordered_qids)
    total_points = _get_total_points(gs.results, rounding_base=config.rounding_base)
    total_max_points = _get_total_max_points(gs.results, rounding_base=config.rounding_base)
    total_percent = _get_total_percent(gs.results, rounding_base=config.rounding_base)
    rounded_total_points = _maybe_round(total_points, config.rounding_base)
    rounded_total_max_points = _maybe_round(total_max_points, config.rounding_base)
    rounded_total_percent = _maybe_round(total_percent, config.rounding_base)
    if config.include_answers:
        for qid in ordered_qids:
            row[qid] = _serialize_answer(gs.answer_map.get(qid, ""))
    if config.include_per_question_results:
        for qid in ordered_qids:
            res = result_by_qid.get(qid)
            if res is None:
                for col in _generate_question_result_columns(qid):
                    row[col] = ""
            else:
                row[f"{qid}__points"] = str(res.points)
                row[f"{qid}__max_points"] = str(res.max_points)
                row[f"{qid}__passed"] = "TRUE" if res.passed else "FALSE"
                percent = _get_total_percent([res], rounding_base=config.rounding_base)
                row[f"{qid}__percent"] = f"{percent}" if res.max_points > 0 else "N/A"
    if config.include_feedback:
        for qid in ordered_qids:
            res = result_by_qid.get(qid)
            row[f"{qid}__feedback"] = (res.feedback or "") if res else ""
    if config.include_remarks:
        row["remarks"] = _remarks(ordered_results, total_points, total_max_points, total_percent)
        if config.include_rounded_total:
            row["remarks"] += f"""
Rounded Total: {rounded_total_points}/{rounded_total_max_points} points | {rounded_total_percent}%
"""
    if config.include_total:
        row["total_points"] = str(total_points)
        row["total_max_points"] = str(total_max_points)
        row["total_percent"] = str(total_percent)
    if config.include_rounded_total:
        row["rounded_total_points"] = str(rounded_total_points)
        row["rounded_total_max_points"] = str(rounded_total_max_points)
        row["rounded_total_percent"] = str(rounded_total_percent)
    return row


class CsvGradedSubmissionsSerializer(Serializer[Iterable[GradedSubmission]]):
    format = "csv"
    media_type = "text/csv"
    config: CsvGradedSubmissionsConfig = CsvGradedSubmissionsConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def dumps(self, submissions: Iterable[GradedSubmission]) -> DataBlob:
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
        for gs in subs:
            row = _create_row(gs, ordered_qids, config=self.config)
            writer.writerow(row)
        return DataBlob(
            data=out.getvalue().encode("utf-8"), media_type=self.media_type, extension="csv"
        )

    def loads(self, blob) -> Iterable[GradedSubmission]:
        raise NotImplementedError("Deserializing graded submissions from CSV is not supported.")


graded_submissions_serializer_registry.register("csv", CsvGradedSubmissionsSerializer)
