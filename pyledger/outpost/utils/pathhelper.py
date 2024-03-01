# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

"""Outpost utils path helper module

This module provides a path helper class PathHelper in order to manipulate
Outpost project pat and directories.
"""

import os
from pathlib import Path
import typing as T


class ProjectPathHelper:
    def __init__(self, projectdir: os.PathLike, prefix: T.Optional[os.PathLike] = None) -> None:
        """Constructor

        :param projectdir: Top level project directory
        :type projectdir: os.PathLike
        :param prefix: Install staging prefix, default to None
        :type prefix: os.PathLike, optional

        :raises FileNotFoundError: If projectdir does not exist and/or is not found

        Convert argument projectdir to canonical path
        """
        self._projectdir: Path = Path(projectdir).resolve(strict=True)
        self._prefix: Path = Path(prefix) if prefix is not None else Path("usr", "local")
        # XXX: use "output" here
        self._outputdir: Path = Path(self._projectdir, ".")
        self._sourcedir: Path = Path(self._outputdir, "src")
        self._builddir: Path = Path(self._outputdir, "build")
        self._stagingdir: Path = Path(self._outputdir, "staging")
        self._imagedir: Path = Path(self._outputdir, "image")
        self._downloaddir: Path = Path(self._outputdir, "dl")

    def create_outputdir_layout(self) -> None:
        self._outputdir.mkdir(parents=True, exist_ok=True)
        self._sourcedir.mkdir(parents=True, exist_ok=True)
        self._builddir.mkdir(parents=True, exist_ok=True)
        self._stagingdir.mkdir(parents=True, exist_ok=True)
        self._imagedir.mkdir(parents=True, exist_ok=True)
        self._downloaddir.mkdir(parents=True, exist_ok=True)

    @property
    def projectdir(self) -> Path:
        """Project top level directory
        This directory must exist (created at setup)
        """
        return self._projectdir.resolve(strict=True)

    @property
    def outputdir(self) -> Path:
        """Project output directory
        This directory must exist (created at setup)
        """
        return self._outputdir.resolve(strict=True)

    @property
    def sourcedir(self) -> Path:
        """Project source directory
        This directory must exist (created at setup)
        """
        return self._sourcedir.resolve(strict=True)

    @property
    def builddir(self) -> Path:
        """Project build directory
        This directory must exist (created at setup)
        """
        return self._builddir.resolve(strict=True)

    @property
    def stagingdir(self) -> Path:
        """Project staging directory
        This directory must exist (created at setup)
        """
        return self._stagingdir.resolve(strict=True)

    @property
    def imagedir(self) -> Path:
        """Project image directory
        This directory must exist (created at setup)
        """
        return self._imagedir.resolve(strict=True)

    @property
    def downloaddir(self) -> Path:
        """Project download directory
        This directory must exist (created at setup)
        """
        return self._downloaddir.resolve(strict=True)

    @property
    def bindir(self) -> Path:
        """staging bin directory
        This directory may not exist yet (created at build time)
        """
        return Path(self.stagingdir, self._prefix, "bin").resolve()

    @property
    def libdir(self) -> Path:
        """staging lib directory
        This directory may not exist yet (created at build time)
        """
        return Path(self.stagingdir, self._prefix, "lib").resolve()

    @property
    def datadir(self) -> Path:
        """staging data directory
        This directory may not exist yet (created at build time)
        """
        return Path(self.stagingdir, self._prefix, "share").resolve()

    @property
    def pkgconfigdir(self) -> Path:
        """staging pkgconfig directory
        This directory may not exist yet (created at build time)
        """
        return Path(self.libdir, "pkgconfig").resolve()
