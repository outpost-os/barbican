# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

"""Generate a .cargo/config.toml per cargo app.

Add target specific and per apps compile flags in a config.
"""

from argparse import ArgumentParser
from pathlib import Path
import typing as T

from .install import run_install, argument_parser as install_argument_parser


def argument_parser() -> ArgumentParser:
    parser = install_argument_parser()
    parser.add_argument(
        "--target-file",
        type=Path,
        help="rust target file",
    )
    parser.add_argument(
        "--profile",
        action="store",
        type=str,
        default="release",
        help="cargo build profile",
    )

    return parser


def run(argv: T.List[str]) -> None:
    args = argument_parser().parse_args(argv)
    target: str = args.target_file.read_text().splitlines()[0]
    from_dir: Path = (args.from_dir / target / args.profile).resolve(strict=True)
    run_install(from_dir, args.files, args.suffix)
