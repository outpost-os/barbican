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


# templatebin executable entrypoint, as defined in pyproject.toml
def run():
    """template entry point"""
    print(f"hello from executable, version {__version__}")
