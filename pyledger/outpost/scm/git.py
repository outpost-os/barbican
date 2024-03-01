# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import subprocess
import os

from ..utils import working_directory_attr
from .. import logger

from .scm import ScmBaseClass

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyledger.outpost.package import Package


class Git(ScmBaseClass):
    def __init__(self, package: "Package") -> None:
        super().__init__(package)

    def clone(self) -> None:
        subprocess.run(
            ["git", "clone", "--branch", f"{self.revision}", f"{self.url}", f"{self.name}"]
        )

    def fetch(self) -> None:
        subprocess.run(["git", "fetch", "--all"])

    def checkout(self) -> None:
        subprocess.run(["git", "switch", f"{self.revision}"])

    def git_toplevel_directory(self) -> str:
        """return the git top level directory from cwd"""
        return (
            subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True)
            .stdout.strip()
            .decode()
        )

    @working_directory_attr("sourcedir")
    def is_valid(self) -> bool:
        return self.git_toplevel_directory() == os.getcwd()

    def _download(self) -> None:
        skip_clone = False
        if os.path.isdir(self._package.sourcedir):
            skip_clone = self.is_valid()
            logger.info("Already downloaded, step skipped")

        if not skip_clone:
            self.clone()
            self._package.post_download_hook()

    def _update(self) -> None:
        self.fetch()
        self.checkout()
        self._package.post_update_hook()
