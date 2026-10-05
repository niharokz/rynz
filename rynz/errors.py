"""Errors that point at the file (and line) that caused them."""

from __future__ import annotations

from pathlib import Path


class RynzError(Exception):
    """An error the user can fix. Printed without a traceback."""

    def __init__(self, message: str, path: Path | str | None = None, line: int | None = None):
        self.message = message
        self.path = Path(path) if path else None
        self.line = line
        super().__init__(str(self))

    def __str__(self) -> str:
        where = ""
        if self.path:
            where = str(self.path)
            if self.line:
                where += f":{self.line}"
            where += ": "
        return f"{where}{self.message}"


class ConfigError(RynzError):
    pass


class ContentError(RynzError):
    pass


class BuildError(RynzError):
    """Raised at the end of a build that collected one or more errors."""

    def __init__(self, errors: list[RynzError]):
        self.errors = errors
        count = len(errors)
        super().__init__(f"build failed with {count} error{'s' if count != 1 else ''}")
