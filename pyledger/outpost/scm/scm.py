# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
import os

from .. import logger
from ..utils import working_directory_attr

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..package import Package


class ScmBaseClass(ABC):
    def __init__(self, package: "Package") -> None:
        self._package = package

    @working_directory_attr("project_sourcedir")
    def download(self) -> None:
        logger.info(f"Downloading {self.name} from {self.url}")
        os.makedirs(self.sourcedir, exist_ok=True)
        self._download()

    @working_directory_attr("sourcedir")
    def update(self) -> None:
        logger.info(f"Updating {self.name}")
        self._update()

    @property
    def project_sourcedir(self) -> str:
        return self._package.parent.sourcedir

    @property
    def sourcedir(self) -> str:
        return self._package.sourcedir

    @property
    def name(self) -> str:
        return self._package.name

    @property
    def url(self) -> str:
        return self._package.url

    @property
    def revision(self) -> str:
        return self._package.revision

    @abstractmethod
    def _download(self) -> None:
        pass

    @abstractmethod
    def _update(self) -> None:
        pass
