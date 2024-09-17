# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import logging
from .console import console


class LoggerConfig:
    def __init__(self) -> None:
        self._console_handler = console.log_handler
        # TODO
        # Add file logging capability (always w/ full logs)

        logging.basicConfig(
            level="NOTSET",
            format="%(message)s",
            datefmt="[%X]",
            handlers=[self._console_handler],
        )

    def set_console_log_level(self, level: int | str) -> None:
        print(level)
        self._console_handler.setLevel(level)


log_config = LoggerConfig()
logger = logging.getLogger()
