# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from pathlib import Path
import random
import typing as T

from ..relocation.task_meta import TaskMeta, EXIT_MODES
from ..relocation.elfutils import AppElf
from ..utils import align_to


def run_gen_task_metadata_bin(input: Path, output: Path) -> None:
    elf = AppElf(str(input.resolve()), None)
    meta = TaskMeta()

    meta.magic = int(elf.get_package_metadata("task", "magic_value"), base=16)
    meta.version = 1
    meta.handle.id = random.getrandbits(16)
    meta.priority = int(elf.get_package_metadata("task", "priority"), base=10)
    meta.quantum = int(elf.get_package_metadata("task", "quantum"), base=10)
    meta.capabilities = 0  # XXX todo

    meta.flags.autostart_mode = bool(elf.get_package_metadata("task", "auto_start"))

    for mode in EXIT_MODES:
        enabled = False
        try:
            enabled = bool(elf.get_package_metadata("task", f"exit_{mode}"))
        except Exception:
            pass
        finally:
            if enabled:
                meta.flags.exit_mode = mode
                break

    meta.domain = 0

    meta.s_text, text_size = elf.get_section_info(".text")
    _, ARM_size = elf.get_section_info(".ARM")
    meta.text_size = align_to(text_size, 4) + align_to(ARM_size, 4)
    meta.s_got, meta.got_size = elf.get_section_info(".got")
    # XXX: rodata are included in .text section
    # _, meta.rodata_size = elf.get_section_info(".rodata")
    meta.s_svcexchange, _ = elf.get_section_info(".svcexchange")
    _, meta.data_size = elf.get_section_info(".data")
    _, meta.bss_size = elf.get_section_info(".bss")
    meta.heap_size = int(elf.get_package_metadata("task", "heap_size"), base=16)
    meta.stack_size = int(elf.get_package_metadata("task", "stack_size"), base=16)

    meta.entrypoint_offset = elf.get_symbol_offset_from_section("_start", ".text")
    # TODO
    # meta.finalize_offset = elf.get_symbol_offset_from_section("_exit", ".text")

    # TODO all others fields
    #  - this will be done in the heavy tools in c/c++ (or Rust ?) for
    # consistency/maintainability/robustness reason (code duplication avoidance).

    output.write_bytes(meta.pack())


def run(argv: T.List[str]) -> None:
    parser = ArgumentParser()
    parser.add_argument("output", type=Path, help="output elf file")
    parser.add_argument("input", type=Path, help="partially linked input elf")
    args = parser.parse_args(argv)

    run_gen_task_metadata_bin(args.input, args.output)
