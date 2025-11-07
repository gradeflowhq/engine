from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .base import BaseCsvExportConfig
from .registry import export_registry as registry
from .utils import Mapper, base_csv_export

if TYPE_CHECKING:
    from ..models import GradeDetail, GradeOutput


class SummaryCsvExportConfig(BaseCsvExportConfig):
    type: Literal["csv.summary"] = "csv.summary"


class DetailedCsvExportConfig(BaseCsvExportConfig):
    type: Literal["csv.detailed"] = "csv.detailed"


def summary_csv_export(
    results: "GradeOutput", file_path: Path | str, config: "SummaryCsvExportConfig"
) -> None:
    """Export a summary CSV (one row per student) using base_csv_export."""
    col_map: dict[str, Mapper] = {
        "student_id": Mapper(source="student_id"),
        "total_points": Mapper(source="total_points", transform=lambda v: f"{v:.2f}"),
        "max_points": Mapper(source="max_points", transform=lambda v: f"{v:.2f}"),
        "percentage": Mapper(source="percentage", transform=lambda v: f"{v:.2f}"),
    }
    base_csv_export(
        results=results,
        file_path=file_path,
        column_map=col_map,
        encoding=getattr(config, "encoding", "utf-8"),
    )


def detailed_csv_export(
    results: "GradeOutput", file_path: Path | str, config: "DetailedCsvExportConfig"
) -> None:
    """Export a detailed, flattened CSV (one row per student with per-question groups)."""
    results_obj = results
    col_map: dict[str, Mapper] = {"student_id": Mapper(source="student_id")}

    if not results_obj or not results_obj.results:
        return base_csv_export(
            results=results_obj,
            file_path=file_path,
            column_map=col_map,
            encoding=getattr(config, "encoding", "utf-8"),
        )

    # Build ordered question id list first-seen across students
    ordered_qids: list[str] = []
    for res in results_obj.results:
        for d in res.grade_details:
            qid = getattr(d, "question_id", None)
            if qid is not None and qid not in ordered_qids:
                ordered_qids.append(qid)

    attrs = [
        ("answer", "student_answer"),
        ("correct answer", "correct_answer"),
        ("points awarded", "points_awarded"),
        ("max points", "max_points"),
        ("is correct", "is_correct"),
        ("feedback", "feedback"),
    ]

    def make_getter_for_qattr(qid: str, attr: str):
        def getter(lst: list[GradeDetail]):
            if not lst:
                return None
            for item in lst:
                if getattr(item, "question_id", None) == qid:
                    return getattr(item, attr)
            return None

        return getter

    for qid in ordered_qids:
        for label, attr in attrs:
            header = f"{qid} {label}"
            col_map[header] = Mapper(
                source="grade_details", transform=make_getter_for_qattr(qid, attr)
            )

    base_csv_export(
        results=results_obj,
        file_path=file_path,
        column_map=col_map,
        encoding=getattr(config, "encoding", "utf-8"),
    )


registry.register("csv.summary", summary_csv_export, SummaryCsvExportConfig)
registry.register("csv.detailed", detailed_csv_export, DetailedCsvExportConfig)
