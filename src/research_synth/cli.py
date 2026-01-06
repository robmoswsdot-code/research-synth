from __future__ import annotations

import typer
from research_synth.log import setup_rich_tracebacks
from research_synth.commands.init import init_command
from research_synth.commands.ingest import ingest_command
from research_synth.commands.analyze import analyze_command
from research_synth.commands.report import report_command

app = typer.Typer(no_args_is_help=True, add_completion=False)

@app.callback()
def main() -> None:
    setup_rich_tracebacks()

app.command("init")(init_command)
app.command("ingest")(ingest_command)
app.command("analyze")(analyze_command)
app.command("report")(report_command)
