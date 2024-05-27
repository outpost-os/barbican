# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

"""template module.

This module provides utility functions for:
  - XXX

This exports:
  - XXX
"""

from .__version__ import __version__

__all__ = ["__version__", "Project"]

import logging
from pyledger.logger import ColorLogger  # type: ignore

logging.setLoggerClass(ColorLogger)
logger = logging.getLogger(__name__)
