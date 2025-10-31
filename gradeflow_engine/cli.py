"""
Command-line interface for the grading engine.

Provides commands for grading submissions and validating rubrics.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from . import __version__
from .core import (
    grade as grade_submissions,
)
from .io import (
    export_canvas_csv,
    load_rubric,
    save_results_csv,
    save_results_yaml,
)
from .models import GradeOutput

app = typer.Typer(
    name="gradeflow-engine",
    help="Advanced Grader Engine - Grade digital assessments with complex rules",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"gradeflow-engine version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """Advanced Grader Engine CLI."""
    pass


@app.command()
def grade(
    rubric: Path = typer.Argument(
        ...,
        help="Path to rubric YAML file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    submissions: Path = typer.Argument(
        ...,
        help="Path to submissions CSV file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Path = typer.Option(
        "results.yaml",
        "--out",
        "-o",
        help="Output path for results YAML",
    ),
    student_id_col: str = typer.Option(
        "student_id",
        "--student-col",
        "-s",
        help="Name of student ID column in CSV",
    ),
    csv_summary: Path | None = typer.Option(
        None,
        "--csv-summary",
        help="Also save summary CSV",
    ),
    csv_detailed: Path | None = typer.Option(
        None,
        "--csv-detailed",
        help="Also save detailed CSV",
    ),
    canvas_export: Path | None = typer.Option(
        None,
        "--canvas",
        help="Export Canvas-compatible CSV",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress output except errors",
    ),
):
    """
    Grade submissions using a rubric.

    Loads a rubric and submissions, applies grading rules, and outputs results.

    Example:
        gradeflow-engine grade rubric.yaml submissions.csv -o results.yaml
    """
    try:
        if not quiet:
            console.print("[bold blue]Loading rubric and submissions...[/bold blue]")

        # Load rubric and submissions
        from .io import load_rubric, load_submissions_csv

        rubric_obj = load_rubric(str(rubric))
        submissions_list = load_submissions_csv(str(submissions), student_id_col=student_id_col)

        # Grade submissions with progress tracking
        if not quiet:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Grading {len(submissions_list)} submissions...",
                    total=len(submissions_list),
                )

                def update_progress(current: int, total: int):
                    progress.update(task, completed=current)

                results = grade_submissions(
                    rubric_obj, submissions_list, progress_callback=update_progress
                )
        else:
            # No progress display in quiet mode
            results = grade_submissions(rubric_obj, submissions_list)

        if not quiet:
            console.print(f"[green]✓[/green] Graded {len(results.results)} students")

        # Save main results
        save_results_yaml(results, str(output))
        if not quiet:
            console.print(f"[green]✓[/green] Results saved to {output}")

        # Save optional outputs
        if csv_summary:
            save_results_csv(results, str(csv_summary), include_details=False)
            if not quiet:
                console.print(f"[green]✓[/green] Summary CSV saved to {csv_summary}")

        if csv_detailed:
            save_results_csv(results, str(csv_detailed), include_details=True)
            if not quiet:
                console.print(f"[green]✓[/green] Detailed CSV saved to {csv_detailed}")

        if canvas_export:
            export_canvas_csv(results, str(canvas_export))
            if not quiet:
                console.print(f"[green]✓[/green] Canvas export saved to {canvas_export}")

        # Display summary table
        if not quiet:
            _display_summary_table(results)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1) from e


@app.command()
def validate_rubric(
    rubric: Path = typer.Argument(
        ...,
        help="Path to rubric YAML file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed validation info",
    ),
):
    """
    Validate a rubric YAML or JSON file.

    Checks if the rubric conforms to the schema and all rules are valid.

    Example:
        gradeflow-engine validate-rubric rubric.yaml
    """
    try:
        console.print(f"[bold blue]Validating rubric:[/bold blue] {rubric}")

        # Load and validate
        rubric_obj = load_rubric(str(rubric))

        console.print("[green]✓ Rubric is valid![/green]")

        if verbose:
            console.print("\n[bold]Rubric Details:[/bold]")
            console.print(f"  Name: {rubric_obj.name}")
            console.print(f"  Rules: {len(rubric_obj.rules)}")

            # Count rule types
            rule_types: dict[str, int] = {}
            for rule in rubric_obj.rules:
                rule_type: str = rule.type  # type: ignore[assignment]
                rule_types[rule_type] = rule_types.get(rule_type, 0) + 1

            console.print("\n[bold]Rule Types:[/bold]")
            for rule_type, count in rule_types.items():
                console.print(f"  {rule_type}: {count}")

    except Exception as e:
        console.print(f"[bold red]Validation failed:[/bold red] {str(e)}")
        raise typer.Exit(code=1) from e


def _display_summary_table(results: GradeOutput) -> None:
    """Display a summary table of grading results."""
    table = Table(title="\n📊 Grading Summary")

    table.add_column("Student ID", style="cyan")
    table.add_column("Points", style="green", justify="right")
    table.add_column("Max Points", justify="right")
    table.add_column("Percentage", justify="right")
    table.add_column("Grade", style="bold")

    for result in results.results[:10]:  # Show first 10
        percentage = result.percentage

        # Determine letter grade (simple A-F scale)
        if percentage >= 90:
            grade = "[green]A[/green]"
        elif percentage >= 80:
            grade = "[blue]B[/blue]"
        elif percentage >= 70:
            grade = "[yellow]C[/yellow]"
        elif percentage >= 60:
            grade = "[orange]D[/orange]"
        else:
            grade = "[red]F[/red]"

        table.add_row(
            result.student_id,
            f"{result.total_points:.1f}",
            f"{result.max_points:.1f}",
            f"{percentage:.1f}%",
            grade,
        )

    if len(results.results) > 10:
        table.add_row("...", "...", "...", "...", "...", style="dim")

    console.print(table)

    # Calculate stats
    if results.results:
        avg_percentage = sum(r.percentage for r in results.results) / len(results.results)
        console.print(f"\n[bold]Average:[/bold] {avg_percentage:.1f}%")


if __name__ == "__main__":
    app()
