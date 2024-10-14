# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from .package import Package


class Cargo(Package):
    def __init__(self, name: str, parent_project, config_node: dict, type):
        super().__init__(name, parent_project, config_node, type)

    @property
    def build_options(self) -> list[str]:
        return list()

    def post_download_hook(self): ...

    def post_update_hook(self): ...
