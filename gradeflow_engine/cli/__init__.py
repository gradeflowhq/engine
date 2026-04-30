import typer
from rich.console import Console

app = typer.Typer(help="GradeFlow Engine CLI")
console = Console(width=120)

# Import subcommands to register them with the app
from . import grade as grade  # noqa: E402
from . import infer as infer  # noqa: E402
from . import list as list  # noqa: E402

__all__ = ["app", "console"]
