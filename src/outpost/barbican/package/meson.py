# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from .package import Package


class Meson(Package):
    def __init__(self, name: str, parent_project, config_node: dict, type):
        super().__init__(name, parent_project, config_node, type)
