from rich import box
from rich.table import Table

from ..core import (
    list_available_question_set_adapters,
    list_available_question_set_serializers,
    list_available_raw_submissions_adapters,
    list_available_rubric_adapters,
    list_available_rubric_serializers,
    list_available_submissions_serializers,
)
from . import app, console


@app.command("list")
def list_components() -> None:
    sections = [
        ("Question Set Serializers", list_available_question_set_serializers()),
        ("Rubric Serializers", list_available_rubric_serializers()),
        ("Graded Submissions Serializers", list_available_submissions_serializers()),
        ("Raw Submissions Adapters", list_available_raw_submissions_adapters()),
        ("Question Set Adapters", list_available_question_set_adapters()),
        ("Rubric Adapters", list_available_rubric_adapters()),
    ]
    for title, items in sections:
        console.rule(title)
        table = Table(box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column("Name", style="cyan", no_wrap=True)
        if items:
            for name in items:
                table.add_row(name)
        else:
            table.add_row("<none>")
        console.print(table)
