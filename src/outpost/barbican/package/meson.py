# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import subprocess

from .package import Package
from ..utils import working_directory_attr


class Meson(Package):
    def __init__(self, name: str, parent_project, config_node: dict, type):
        super().__init__(name, parent_project, config_node, type)

    @property
    def build_options(self) -> list[str]:
        opts = list()
        opts.append("--pkgconfig.relocatable")
        opts.append(f"--pkg-config-path={self.pkgconfig_dir}")
        opts.append(f"-Dconfig={str(self._dotconfig)}")
        opts.extend([f"-D{k}={str(v)}" for k, v in self._extra_build_opts.items()])
        return opts

    @working_directory_attr("src_dir")
    def post_download_hook(self):
        subprocess.run(["meson", "subprojects", "download"], capture_output=True)

    @working_directory_attr("src_dir")
    def post_update_hook(self):
        subprocess.run(["meson", "subprojects", "download"], capture_output=True)
        subprocess.run(["meson", "subprojects", "update"], capture_output=True)
