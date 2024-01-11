# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

from .git import Git
from .scm import ScmBaseClass

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyledger.outpost.package import Package

__all__ = ["Git"]

SCM_FACTORY_DICT = {
    "git": Git,
    # TODO tarball, etc.
}


def scm_create(package: "Package") -> ScmBaseClass:
    ScmType = SCM_FACTORY_DICT[package.method]
    return ScmType(package)
