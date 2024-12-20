# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

"""Generate a .cargo/config.toml per cargo app

Add target specific and per apps compile flags in a config.
"""

from argparse import ArgumentParser
from pathlib import Path
import typing as T


def run_cargo_config(rustargs: Path, target: Path, extra_args: str, outdir: Path) -> None:
    target = target.read_text().splitlines()[0]
    rustargs = rustargs.read_text().splitlines()
    rustargs.extend(extra_args.split(" "))
    linkerargs = list(filter(lambda x: x.startswith("-Clinker"), rustargs))
    linker = linkerargs[0].split("=")[1] if len(linkerargs) else "is not set"
    rustargs = list(filter(lambda x: not x.startswith("-Clinker"), rustargs))

    config = f"""
[build]
target = "{target}"
target-dir = "{str(outdir.resolve())}"
rustflags = {rustargs}

[target.{target}]
{"#" if not len(linkerargs) else ""}linker = "{linker}"

[env]
OUT_DIR = "{str(outdir.resolve())}"
"""

    (outdir / ".cargo" / "config.toml").write_text(config)


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("--rustargs-file", type=Path, help="rustargs file path")
    parser.add_argument("--target-file", type=Path, help="rust target file path")
    parser.add_argument("--extra-args", type=str)
    parser.add_argument("outdir", type=Path, help="output directory")

    return parser


def run(argv: T.List[str]) -> None:
    """Execute gen crate cargo config command."""
    args = argument_parser().parse_args(argv)
    run_cargo_config(args.rustargs_file, args.target_file, args.extra_args, args.outdir)
