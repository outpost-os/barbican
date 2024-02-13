# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import logging
import shutil
import typing as T

from .. import logger


_PROGRAM_CACHE_DICT: dict[str | bytes, str | bytes] = {}


def find_program(
    programe_name: str | bytes, required: bool = True, path: T.Optional[str] = None
) -> T.Optional[str | bytes]:
    if programe_name in _PROGRAM_CACHE_DICT.keys():
        return _PROGRAM_CACHE_DICT[programe_name]

    log = f"Find Program: {programe_name!r}"
    if path:
        log += f" (alt. path: {path})"
    program_cmd = shutil.which(programe_name, path=path)
    log += ": OK" if program_cmd else ": NOK"
    log_level = logging.INFO if program_cmd else logging.ERROR
    logger.log(log_level, log)

    if required and not program_cmd:
        raise Exception("Required program not found")

    if not program_cmd:
        _PROGRAM_CACHE_DICT[programe_name] = T.cast(str | bytes, program_cmd)

    return program_cmd
