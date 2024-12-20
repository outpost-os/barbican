# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

"""Generate a .cargo/config.toml per cargo app.

Add target specific and per apps compile flags in a config.
"""

from argparse import ArgumentParser
from pathlib import Path
import typing as T


def run_cargo_config(rustargs: Path, target: Path, extra_args: str, outdir: Path) -> None:
    rust_target = target.read_text().splitlines()[0]
    rust_flags = rustargs.read_text().splitlines()
    rust_flags.extend(extra_args.split(" "))
    linker_args = list(filter(lambda x: x.startswith("-Clinker"), rust_flags))
    linker = linker_args[0].split("=")[1] if len(linker_args) else "is not set"
    rust_flags = list(filter(lambda x: not x.startswith("-Clinker"), rust_flags))

    config = f"""
[build]
target = "{rust_target}"
target-dir = "{str(outdir.resolve())}"
rustflags = {rust_flags}

[target.{rust_target}]
{"#" if not len(linker_args) else ""}linker = "{linker}"

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
