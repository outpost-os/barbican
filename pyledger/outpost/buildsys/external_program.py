# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

"""
External programs helper for build system file generation.
As this is not tied the the chosen backend, this is a separate module.
"""

from pyledger.outpost.utils import find_program

# XXX: may be forge this list according to project option
# there is no need now, but for future use ?
_EXTERNAL_PROGRAMS_NAME = [
    "outpost",
    "git",
    "meson",
    "ninja",
    "srec_cat",
]

_EXTERNAL_PROGRAMS = dict()

def external_programs_initialize() -> None:
    for name in _EXTERNAL_PROGRAMS_NAME:
        _EXTERNAL_PROGRAMS[name] = find_program(name)

def external_program_get(name: str) -> str | None:
    return _EXTERNAL_PROGRAMS.get(name)
