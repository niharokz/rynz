"""The single place rynz prints to the terminal."""

from __future__ import annotations

from rich.console import Console

_console = Console(highlight=False)
_err = Console(stderr=True, highlight=False)
_level = 1  # 0 = quiet, 1 = normal, 2 = verbose


def set_level(quiet: bool = False, verbose: bool = False) -> None:
    global _level
    _level = 0 if quiet else 2 if verbose else 1


def info(message: str) -> None:
    if _level >= 1:
        _console.print(message)


def ok(message: str) -> None:
    if _level >= 1:
        _console.print(f"[green]✓[/green] {message}")


def debug(message: str) -> None:
    if _level >= 2:
        _console.print(f"[dim]{message}[/dim]")


def warn(message: str) -> None:
    _err.print(f"[yellow]warning:[/yellow] {message}")


def error(message: str) -> None:
    _err.print(f"[bold red]error:[/bold red] {message}")


def table(title: str, rows: list[tuple[str, str]]) -> None:
    from rich.table import Table

    t = Table(title=title, show_header=False, title_justify="left")
    t.add_column(style="cyan")
    t.add_column()
    for key, value in rows:
        t.add_row(key, value)
    _console.print(t)
