# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
import subprocess

from ..scm import scm_create
from ..utils import working_directory_attr

import typing as T

if T.TYPE_CHECKING:
    from pyledger.outpost.outpost import Project


class Package:
    def __init__(
        self, name: str, parent_project: "Project", config_node: dict, is_app: bool = False
    ) -> None:
        self._name = name
        self._parent = parent_project
        self._config = config_node
        self._scm = scm_create(self)
        # True if package is an user app, False if sys package
        self._is_app = is_app

        self._exelist: list[str] = (
            self._config["exelist"] if "exelist" in self._config.keys() else []
        )

        self._dts_include_dirs = [Path(self.sourcedir) / "dts"]
        if "extra_dts_incdir" in self._config:
            self._dts_include_dirs.extend(self._config["extra_dts_incdir"])

        dotconfig = Path(self._config["config_file"])
        if not dotconfig.exists():
            dotconfig = Path(self.sourcedir) / dotconfig.relative_to(parent_project.topdir)

        self._dotconfig = dotconfig.resolve()

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_app_package(self) -> bool:
        return self._is_app

    @property
    def is_sys_package(self) -> bool:
        return not self._is_app

    @property
    def sourcedir(self) -> str:
        return os.path.join(self._parent.sourcedir, self.name)

    @property
    def builddir(self) -> str:
        return os.path.join(self._parent.builddir, self.name)

    @property
    def stagingdir(self) -> str:
        return self._parent.stagingdir

    @property
    def pkgconfigdir(self) -> str:
        # XXX: define a prefix instead of usr/local which is the default meson prefix
        return os.path.join(self.stagingdir, "usr/local", "lib/pkgconfig")

    @property
    def bindir(self) -> str:
        return self._parent.bindir

    @property
    def libdir(self) -> str:
        return self._parent.libdir

    @property
    def datadir(self) -> str:
        return os.path.join(self._parent.datadir, self.name.replace("lib", "", 1))

    @property
    def built_exelist(self) -> list[Path]:
        return [Path(self.builddir) / exe for exe in self._exelist]

    @property
    def installed_exelist(self) -> list[Path]:
        return [Path(self.bindir) / exe for exe in self._exelist]

    @property
    def dummy_linked_exelist(self) -> list[Path]:
        dummy_list = []
        for exe in self._exelist:
            exe_path = Path(self._parent.builddir) / exe
            new_suffix = ".dummy" + exe_path.suffix
            dummy_list.append(exe_path.with_suffix(new_suffix))

        return dummy_list

    @property
    def relocated_exelist(self) -> list[Path]:
        return [Path(self._parent.builddir) / exe for exe in self._exelist]

    @property
    def dts_include_dirs(self) -> list[Path]:
        return self._dts_include_dirs

    @property
    def parent(self):
        return self._parent

    @property
    def deps(self):
        # XXX sanity checks
        return self._config["deps"] if "deps" in self._config else list()

    @property
    def build_opts(self):
        build_opts = list()
        build_opts.append("--pkgconfig.relocatable")
        build_opts.append(f"--pkg-config-path={self.pkgconfigdir}")
        build_opts.append(f"-Dconfig={str(self._dotconfig)}")
        build_opts.append(self._config["build_opts"] if "build_opts" in self._config else list())
        return build_opts

    def download(self) -> None:
        self._scm.download()

    def update(self) -> None:
        self._scm.update()

    def __getattr__(self, attr):
        return self._config[attr] if attr in self._config else None

    @working_directory_attr("sourcedir")
    def post_download_hook(self):
        subprocess.run(["meson", "subprojects", "download"])

    @working_directory_attr("sourcedir")
    def post_update_hook(self):
        subprocess.run(["meson", "subprojects", "download"])
        subprocess.run(["meson", "subprojects", "update"])
