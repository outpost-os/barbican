# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from pathlib import Path


class ScmBaseClass(ABC):
    def __init__(self, name: str, src_dir: Path, config: dict) -> None:
        self._name = name
        self._src_dir = src_dir
        self._config = config

    @property
    def project_sourcedir(self) -> Path:
        return self._src_dir

    @property
    def sourcedir(self) -> Path:
        return self._src_dir / self.name

    @property
    def name(self) -> str:
        return self._name

    @property
    def url(self) -> str:
        return self._config["uri"]

    @property
    def revision(self) -> str:
        return self._config["revision"]

    @abstractmethod
    def download(self) -> None: ...

    @abstractmethod
    def update(self) -> None: ...
