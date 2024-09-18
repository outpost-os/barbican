# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from enum import auto, unique
import collections.abc
from .scm import ScmBaseClass
from ..utils import StrEnum

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..package import Package

__all__ = ["Git"]


@unique
class ScmMethodEnum(StrEnum):
    Git = auto()


class ScmMethodFactoryMap(collections.abc.Mapping[ScmMethodEnum, collections.abc.Callable]):
    def __init__(self) -> None:
        self._key_type = ScmMethodEnum

    def __len__(self):
        return len(self._key_type)

    def __iter__(self):
        yield from [k.value for k in list(self._key_type)]

    def __getitem__(self, key):
        method = self._key_type(key)

        from importlib import import_module
        import sys

        return getattr(
            import_module("." + method.value, sys.modules[__name__].__name__), method.name
        )


SCM_FACTORY_DICT = ScmMethodFactoryMap()


def scm_create(package: "Package") -> ScmBaseClass:
    ScmType = SCM_FACTORY_DICT[package.method]
    return ScmType(package)
