# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: LicenseRef-LEDGER

# coding: utf-8

# import pytest

from pyledger.template.subpkg import templater


def test_hello():
    """Test word counting from a file."""
    handle = templater()
    handle.hello("the universe number is ")


def test_bye():
    """Test word counting from a file."""
    handle = templater()
    handle.goodbye()
