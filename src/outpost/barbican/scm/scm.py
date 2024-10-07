# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
import os

from ..logger import logger
from ..utils import working_directory_attr

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..package import Package


# XXX:
#  Need API change
#  Use config node as argument as it depends on SCM derived class
#  At least, `name` and `sourcedir` are common among SCMs


class ScmBaseClass(ABC):
    def __init__(self, package: "Package", config: dict) -> None:
        self._package = package
        self._config = config

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
    def project_sourcedir(self) -> Path:
        return self._package.parent.path.src_dir

    @property
    def sourcedir(self) -> Path:
        return self._package.src_dir

    @property
    def name(self) -> str:
        return self._package.name

    @property
    def url(self) -> str:
        return self._config["uri"]

    @property
    def revision(self) -> str:
        return self._config["revision"]

    @abstractmethod
    def _download(self) -> None:
        pass

    @abstractmethod
    def _update(self) -> None:
        pass
