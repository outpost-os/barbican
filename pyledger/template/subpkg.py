# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: LicenseRef-LEDGER

# coding: utf-8


# TODO: Move the imports out. setup related
class templater:
    def __init__(self):
        self._private_var = 42

    def hello(self, prefix):
        print(str(prefix) + str(self._private_var))

    def goodbye(self):
        pass
