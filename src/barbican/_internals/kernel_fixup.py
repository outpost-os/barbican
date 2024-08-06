# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from pathlib import Path
import typing as T

from ..relocation.elfutils import SentryElf


def run_kernel_fixup(kern_input: Path, kern_output: Path, metadata: list[Path]) -> None:
    kernel = SentryElf(str(kern_input.resolve(strict=True)), str(kern_output.resolve()))
    task_meta_tbl = bytearray()

    for datum in metadata:
        blob = datum.read_bytes()

        # XXX:
        # fixme
        # put table size in sentry elf in order to retrieve padding between entries
        task_meta_tbl.extend(blob)
        if len(blob) % 8:
            task_meta_tbl.extend(bytes([0] * (len(blob) % 8)))

    kernel.patch_task_list(task_meta_tbl)
    kernel.save()


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("kern_output", type=Path, help="fixed up kernel elf file")
    parser.add_argument("kern_input", type=Path, help="kernel elf file")
    parser.add_argument("metadata", type=Path, nargs="+", help="metadata bin files")

    return parser


def run(argv: T.List[str]) -> None:
    """Execute kernel_fixup internal command."""
    args = argument_parser().parse_args(argv)
    run_kernel_fixup(args.kern_input, args.kern_output, args.metadata)
