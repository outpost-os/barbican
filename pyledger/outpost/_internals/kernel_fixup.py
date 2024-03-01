# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from pathlib import Path
import typing as T

from ..relocation.elfutils import SentryElf


def run_kernel_fixup(kern_input: Path, kern_output: Path, metadata: list[Path]) -> None:
    kernel = SentryElf(str(kern_input.resolve(strict=True)), str(kern_output.resolve()))
    task_meta_tbl = bytearray()

    for datum in metadata:
        task_meta_tbl.extend(datum.read_bytes())

    kernel.patch_task_list(task_meta_tbl)
    kernel.save()


def run(argv: T.List[str]) -> None:
    """Execute gen_ldscript internal command"""
    parser = ArgumentParser()

    parser.add_argument("kern_output", type=Path, help="fixed up kernel elf file")
    parser.add_argument("kern_input", type=Path, help="kernel elf file")
    parser.add_argument("metadata", type=Path, nargs="+", help="metadata bin files")

    args = parser.parse_args(argv)
    run_kernel_fixup(args.kern_input, args.kern_output, args.metadata)
