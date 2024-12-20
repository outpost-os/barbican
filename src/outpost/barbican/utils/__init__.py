# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import os
import math

from contextlib import contextmanager
from enum import Enum
from pathlib import Path

from ..logger import logger


# XXX:
#  StrEnum is a python 3.11+ feature but as simple as the following.
try:
    from enum import StrEnum  # type: ignore
except ImportError:

    class StrEnum(Enum):  # type: ignore
        @staticmethod
        def _generate_next_value_(  # type: ignore
            name: str, start: int, count: int, last_values: list[str]
        ) -> str:
            return name.replace("_", "-").lower()


@contextmanager
def working_directory(path: Path):
    prev = Path.cwd()
    if not path.is_dir():
        raise NotADirectoryError
    next = path.resolve()
    logger.debug(f"entering {str(next)} ...")
    os.chdir(next)
    try:
        yield
    finally:
        logger.debug(f"... leaving {next}")
        os.chdir(prev)


def working_directory_attr(attr):
    """Change working dir for the decorated function.

    Enter a new dir and leave after function call the directory is a property (attr) of an object.
    """

    def _working_directory(func):
        def wrapper(self, *args, **kwargs):
            with working_directory(Path(getattr(self, attr))):
                return func(self, *args, **kwargs)

        return wrapper

    return _working_directory


def pow2_round_up(x: int) -> int:
    """Round number to the next power of 2 boundary."""
    return 1 if x == 0 else 2 ** math.ceil(math.log2(x))


def pow2_greatest_divisor(x: int) -> int:
    """Return the highest power of 2 than can divide x."""
    return math.gcd(x, pow2_round_up(x))


def align_to(x: int, a: int) -> int:
    return ((x + a - 1) // a) * a
