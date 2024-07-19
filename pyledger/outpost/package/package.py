# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
import subprocess
from functools import lru_cache

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

        self._dts_include_dirs = [Path(self.src_dir) / "dts"]
        if "extra_dts_incdir" in self._config:
            # extra dts includedir are source package relative
            self._dts_include_dirs.extend(
                [Path(self.src_dir) / d for d in self._config["extra_dts_incdir"]]
            )

        dotconfig = Path(self._config["config_file"])
        if dotconfig.is_absolute():
            # XXX proper execpetion handling
            raise Exception("config file must be project top level relative file")

        # XXX: Enforce path rel to project configs dir
        self._dotconfig = (Path(self._parent.path.project_dir) / dotconfig).resolve(strict=True)

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
    @lru_cache
    def src_dir(self) -> Path:
        return self._parent.path.src_dir / self.name

    @property
    @lru_cache
    def build_dir(self) -> Path:
        return self._parent.path.build_dir / self.name

    @property
    @lru_cache
    def staging_dir(self) -> Path:
        return self._parent.path.staging_dir

    @property
    @lru_cache
    def pkgconfig_dir(self) -> Path:
        return self._parent.path.sysroot_pkgconfig_dir

    @property
    @lru_cache
    def bin_dir(self) -> Path:
        return self._parent.path.target_bin_dir

    @property
    @lru_cache
    def lib_dir(self) -> Path:
        return self._parent.path.sysroot_lib_dir

    @property
    @lru_cache
    def data_dir(self) -> Path:
        return self._parent.path.sysroot_data_dir / self.name.replace("lib", "", 1)

    @property
    def built_exelist(self) -> list[Path]:
        return [Path(self.build_dir) / exe for exe in self._exelist]

    @property
    def installed_exelist(self) -> list[Path]:
        return [Path(self.bin_dir) / exe for exe in self._exelist]

    @property
    def dummy_linked_exelist(self) -> list[Path]:
        dummy_list = []
        for exe in self._exelist:
            exe_path = self._parent.path.private_build_dir / exe
            new_suffix = ".dummy" + exe_path.suffix
            dummy_list.append(exe_path.with_suffix(new_suffix))

        return dummy_list

    @property
    def relocated_exelist(self) -> list[Path]:
        return [Path(self._parent.path.private_build_dir) / exe for exe in self._exelist]

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
        build_opts.append(f"--pkg-config-path={self.pkgconfig_dir}")
        build_opts.append(f"-Dconfig={str(self._dotconfig)}")
        build_opts.append(self._config["build_opts"] if "build_opts" in self._config else list())
        return build_opts

    def download(self) -> None:
        self._scm.download()

    def update(self) -> None:
        self._scm.update()

    def __getattr__(self, attr):
        return self._config[attr] if attr in self._config else None

    @working_directory_attr("src_dir")
    def post_download_hook(self):
        subprocess.run(["meson", "subprojects", "download"], capture_output=True)

    @working_directory_attr("src_dir")
    def post_update_hook(self):
        subprocess.run(["meson", "subprojects", "download"], capture_output=True)
        subprocess.run(["meson", "subprojects", "update"], capture_output=True)
