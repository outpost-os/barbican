# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import os
import math
import typing as T
from enum import Enum

from ..logger import logger


# XXX:
#  StrEnum is a python 3.11+ feature but as simple as the following.
try:
    from enum import StrEnum  # type: ignore
except ImportError:

    class StrEnum(Enum):  # type: ignore
        @staticmethod
        def _generate_next_value_(
            name: str, start: int, count: int, last_values: list[T.Any]
        ) -> T.Any:
            return name.replace("_", "-").lower()


class _WorkingDir:
    """Helper class for the following decorators.

    Parameters
    ----------
    working_dir: str
    """

    def __init__(self, working_dir: str) -> None:
        self._prev = os.getcwd()
        self._next = working_dir

    def enter(self) -> None:
        logger.debug(f"enterring {self._next} ...")
        self._prev = os.getcwd()
        os.chdir(self._next)

    def leave(self) -> None:
        os.chdir(self._prev)
        logger.debug(f"... leaving {self._next}")


def working_directory(path):
    """Change working dir for the decorated function.

    Enter a new dir and leave after function call the directory is a decorator argument.
    """

    def _working_directory(func):
        def wrapper(*args, **kwargs):
            try:
                wd = _WorkingDir(path)
                wd.enter()
                ret = func(*args, **kwargs)
            except Exception:
                raise
            finally:
                wd.leave()
            return ret

        return wrapper

    return _working_directory


def working_directory_attr(attr):
    """Change working dir for the decorated function.

    Enter a new dir and leave after function call the directory is a property (attr) of an object.
    """

    def _working_directory(func):
        def wrapper(self, *args, **kwargs):
            try:
                wd = _WorkingDir(getattr(self, attr))
                wd.enter()
                ret = func(self, *args, **kwargs)
            except Exception:
                raise
            finally:
                wd.leave()
            return ret

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
