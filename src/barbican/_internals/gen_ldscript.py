# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

"""Generate LD script internal command.

TODO : documentation
"""

from argparse import ArgumentParser
from pathlib import Path
import typing as T

from jinja2 import Environment, BaseLoader
import json


def run_gen_ldscript(name: str, template: Path, layout: Path, output: Path) -> None:
    """LD script generator internal command.

    This command generate a linker script for an barbican application based on the
    linker script template provides by libshield (TODO sphinx cross ref) (in noPIC build mode)
    to be used by :py:mod:`.relink_elf` internal. The template is processed by jinja2 with the
    memory layout generated by :py:mod:`.gen_memory_layout` internal.

    Parameters
    ----------
    name: str
        application name
    template: Path
        linker script Jinja2 template
    layout: Path
        barbican memory layout in json
    output: Path
        generated linker script for a given application
    """
    with open(layout, "r", encoding="utf-8") as layout_file:
        memory_layout = json.load(layout_file)
        with open(template, "r") as template_file:
            linkerscript_template = Environment(loader=BaseLoader()).from_string(
                template_file.read()
            )
            with open(output, "w", encoding="utf-8") as linkerscript:
                linkerscript.write(linkerscript_template.render(name=name, layout=memory_layout))


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("--name", type=str, action="store", help="application name")
    parser.add_argument("template", type=Path, help="ld script template")
    parser.add_argument("layout", type=Path, help="memory layout (in json format)")
    parser.add_argument("output", type=Path, help="output filename")

    return parser


def run(argv: T.List[str]) -> None:
    """Execute gen_ldscript internal command."""
    args = argument_parser().parse_args(argv)
    run_gen_ldscript(args.name, args.template, args.layout, args.output)
