from __future__ import annotations

from rich.console import Console
from rich.traceback import install

console = Console()

def setup_rich_tracebacks() -> None:
    install(console=console, show_locals=True, suppress=["typer", "click"])
