# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: LicenseRef-LEDGER

# coding: utf-8
"""template module.

This module provides utility functions for:
  - XXX

This exports:
  - XXX
"""

from .__version__ import __version__

__all__ = ["__version__"]

import logging
from pyledger.logger import ColorLogger

logging.setLoggerClass(ColorLogger)
logger = logging.getLogger(__name__)

def run():
    from .outpost import Project

    project = Project("project.toml")
    project.download()
    project.setup()
