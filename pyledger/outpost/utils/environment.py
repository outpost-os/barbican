# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import logging
import shutil
import typing as T
from pathlib import Path

from .. import logger


_PROGRAM_CACHE_DICT: dict[str | bytes, str | bytes] = {}


@T.overload
def find_program(name: str) -> str:
    ...


@T.overload
def find_program(name: bytes) -> bytes:
    ...


@T.overload
def find_program(name: str, path: T.Optional[Path]) -> str:
    ...


@T.overload
def find_program(name: bytes, path: T.Optional[Path]) -> bytes:
    ...


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
