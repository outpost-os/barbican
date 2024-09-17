# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

"""Barbican internal commands.

This subpackage holds internal commands infrastructure.
Those commands are called from ninja build script.

.. note::
    Internal commands are not listed by `barbican help`.

One can call internal command with the following:

.. code-block:: console

    barbican --internal <cmd> [<args...>]

.. note::
    | `cmd` is the module name in :py:mod:`._internals` subpackage.
    | `args...` is the internal command argument list.

.. admonition:: Add internal command
    :class: tip

        Create a new module, module name is the internal command name.
        This module must have, at least, the following methods:

        .. function:: argument_parser() -> ArgumentParser:

            Returns the Python's :py:type:`argparse.ArgumentParser` for the given internal command

        .. function:: run(argv: T.List[str]) -> None:

            Execute the internal command.
"""
