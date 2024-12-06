# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser, REMAINDER
from pathlib import Path
import shutil
import typing as T

from ..console import console


def run_install(from_dir: Path, files: list[Path], suffix: str = ""):
    for f in files:
        src = (from_dir / f.name).resolve(strict=True)
        dest = f.with_suffix(suffix)
        if not dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
        console.message(f"Installing [i]{str(src)}[/i]→ [i]{str(dest)}[/i]")
        shutil.copy2(src, dest)


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument(
        "-s",
        "--suffix",
        action="store",
        type=str,
        default="",
        help="suffix to append to the installed file(s)",
    )
    parser.add_argument("from_dir", type=Path, help="directory from where files are installed")
    parser.add_argument("files", nargs=REMAINDER, type=Path, help="file(s) install destination")

    return parser


def run(argv: T.List[str]) -> None:
    args = argument_parser().parse_args(argv)
    run_install(args.from_dir, args.files, args.suffix)
