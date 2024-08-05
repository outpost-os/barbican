# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any

import rich
import rich.progress
import rich.status
import rich.logging
import rich.text


class Console:
    """Rich console wrapper."""

    def __init__(self) -> None:
        self._theme = rich.theme.Theme(
            {
                "title": "bold underline",
                "warning": "bold dark_orange3",
                "error": "bold red3",
                "critical": "bold dark_magenta",
                "deprecated": "bold gold1",
            }
        )
        self._console = rich.console.Console(theme=self._theme)
        self._log_handler = rich.logging.RichHandler(
            level=logging.CRITICAL,
            rich_tracebacks=True,
            console=self._console,
        )

    @property
    def log_handler(self) -> logging.Handler:
        return self._log_handler

    @staticmethod
    def _raw_message(message: str) -> str:
        """
        Return message without rich markup.

        Parameters
        ----------
        message:    str
                    A string containing rich console markup

        Returns
        -------
        str
            Plain text (i.e. without rich markup)
        """
        return rich.text.Text.from_markup(message).plain

    @staticmethod
    def _log(level: int, message: str) -> None:
        """
        Log a message with default logger.

        Parameters
        ----------
        level: int
               Log Level as defined by built-in logging module
        message: str
                 message to log
        """
        logging.getLogger().log(level, Console._raw_message(message))

    def _theme2level(self, theme: str) -> int:
        if theme not in self._theme.styles.keys():
            raise ValueError
        elif theme == "title":
            return logging.DEBUG
        elif theme == "deprecated":
            return logging.WARNING
        else:
            return logging.getLevelName(theme.upper())

    def title(self, message: str) -> None:
        self._log(logging.DEBUG, message)
        self._console.print(message, style="title")

    def message(self, message: str) -> None:
        self._log(logging.INFO, message)
        self._console.print(f"{message}")

    def __getattr__(self, name: str) -> Any:
        def __default(message) -> None:
            self._log(self._theme2level(name), message)
            self._console.print(
                f"[u]{name.upper()}[/u]: [not bold]{message}[/not bold]", style=name
            )

        return __default

    def progress_bar(self, transient: bool = False) -> rich.progress.Progress:
        return rich.progress.Progress(
            rich.progress.SpinnerColumn(),
            rich.progress.TextColumn("[progress.description]{task.description}"),
            rich.progress.BarColumn(),
            rich.progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            "eta",
            rich.progress.TimeRemainingColumn(),
            rich.progress.TextColumn("{task.fields[message]}"),
            transient=transient,
            console=self._console,
        )

    def status(self, message: str) -> rich.status.Status:
        return rich.status.Status(message, spinner="moon", console=self._console)


console = Console()
