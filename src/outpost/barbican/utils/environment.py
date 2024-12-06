# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import logging
import shutil
import typing as T
from pathlib import Path
from subprocess import run

from ..logger import logger


_PROGRAM_CACHE_DICT: dict[str | bytes, str | bytes] = {}


@T.overload
def find_program(name: str) -> str: ...
@T.overload
def find_program(name: bytes) -> bytes: ...
@T.overload
def find_program(name: str, path: T.Optional[Path]) -> str: ...
@T.overload
def find_program(name: bytes, path: T.Optional[Path]) -> bytes: ...


def find_program(name: str | bytes, path: T.Optional[Path] = None) -> str | bytes:
    if name not in _PROGRAM_CACHE_DICT.keys():
        log = f"Find Program: {name!r}"
        if path:
            log += f" (alt. path: {path})"
        cmd = shutil.which(name, path=path)
        log += ": OK" if cmd else ": NOK"
        log_level = logging.INFO if cmd else logging.ERROR
        logger.log(log_level, log)

        if not cmd:
            raise Exception("Required program not found")

        _PROGRAM_CACHE_DICT[name] = cmd

    return _PROGRAM_CACHE_DICT[name]


class ExeWrapper:
    """Wrap call to an external program.

    This wrapper allows user to call a external program in a python way without
    forging command line by hand.

    This class is callable w/ a set of keyword arguments (REF), other keyword arguments
    are converted to command line options. If there is sub commands, one can call
    the sub command using its name as object attribute.

    Examples
    --------
    >>> meson = ExeWrapper("meson")
    >>> meson(version=True)
    1.4.2
    >>> meson.setup(cross_file="Path/to/crossfile", args=["path/to/builddir"])
    """

    def __init__(self, name: str, path: T.Optional[Path] = None, capture_out: bool = False) -> None:
        """Initialize a ExeWrapper instance.

        Parameters
        ----------
        name: str
            Program name to wrap
        path: T.Optional[Path]
            Search path for executable, optional.
        capture_out: bool
            Capture stdout as str (system default encoding) if True, False by default.
        """
        self.exe = find_program(name, path)
        self._capture_out = capture_out

    def __getattr__(self, name):
        return lambda *args, **kwargs: self._execute(name, *args, **kwargs)

    def __call__(self, **kwargs) -> None:
        self._execute(cmd="", **kwargs)

    def _execute(
        self,
        cmd: str,
        *,
        subcmd: list[str] = list(),
        args: list[str] = list(),
        extra_opts: dict = dict(),
        extra_args: list[str] = list(),
        **kwargs,
    ) -> str | None:
        """Forge command line and execute.

        The forged command line is the following:

        .. code-block:: text

            exe_path [<cmd>] [<subcmds>...] [<**kwargs>...] [<args>...] [ -- [<extra_opts>...]
            [<extra_args>...]]

        Note
        ----
        Options (i.e. kwargs) and extra_options are converted to GNU short or long option based on
        option name length.

        Parameters
        ----------
        cmd: str
            command name, optional, may be empty string
        subcmd: list[str]
            list of extra sub command if any
        args: list[str]
            list of string argument to pass to the command
        extra_opts: dict
            dictionary of extra option to append after double dash if any
        extra_args: list[str]
            list of extra arguments to append after double dash if any
        **kwargs:
            variadic keyword arguments translate into command options

        Note
        ----
        Double dash means end of options and usually used to add options and args to an internally
        called program, or arguments with leading dash that will be interpreted as options
        otherwise.

        Warning
        -------
        Underscores are translate to dashes in options name. By convention, dash are used as
        separator.

        Returns
        -------
        str | None
            captured stdout as string or None if capture_out is false
        """

        def to_options_list(**kwargs) -> list[str]:
            options: list[str] = list()
            for option, value in kwargs.items():
                options.append(f"{'--' if len(option) > 1 else '-'}{option.replace('_', '-')}")
                if value is True:
                    continue
                elif value is not False and value is not None:
                    options.append(str(value))
            return options

        cmdline = [self.exe, cmd]
        cmdline.extend(subcmd)
        cmdline.extend(to_options_list(**kwargs))
        cmdline.extend(args)
        if len(extra_args) or len(extra_opts):
            cmdline.append("--")
        if len(extra_args):
            cmdline.extend(*extra_args)
        if len(extra_opts):
            cmdline.extend(to_options_list(**extra_opts))
        logger.debug(cmdline)
        result = run(
            cmdline,
            check=True,
            capture_output=self._capture_out,
            text=self._capture_out,
        )

        return result.stdout
