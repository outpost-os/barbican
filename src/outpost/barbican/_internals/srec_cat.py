# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

"""srec_cat internal command.

TODO : documentation
"""

from argparse import ArgumentParser
from pathlib import Path
import typing as T

import subprocess

from ..utils.environment import find_program


_SREC_CAT_FORMAT: T.Dict[str, str] = {
    "ihex": "-intel",
}


def run_srec_cat(inputs: T.List[Path], output: Path, format: str) -> None:
    srec_cat = find_program("srec_cat")
    cmdline: T.List[str] = [srec_cat]

    for input in inputs:
        cmdline.extend([str(input.resolve(strict=True)), format])

    cmdline.extend(["-o", str(output.resolve()), format])
    subprocess.run(cmdline, check=True)


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument(
        "--format",
        type=str,
        choices=_SREC_CAT_FORMAT.keys(),
        required=True,
        help="file format to use",
    )
    parser.add_argument("output", type=Path, help="concatenate resulting file")
    parser.add_argument("inputs", type=Path, nargs="+", help="input file(s) to concatenate")

    return parser


def run(argv: T.List[str]) -> None:
    """Execute srec_cat internal command."""
    args = argument_parser().parse_args(argv)
    run_srec_cat(args.inputs, args.output, _SREC_CAT_FORMAT[args.format])
