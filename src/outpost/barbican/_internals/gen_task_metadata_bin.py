# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
import json
import os
from pathlib import Path
import subprocess
import typing as T

from ..utils.environment import find_program
from ..utils.pathhelper import ProjectPath
from ..relocation.elfutils import AppElf
from ..utils import align_to


def _gen_metadata(output: Path, metadata: dict[str, T.Any], path: ProjectPath) -> None:
    # XXX:
    # Path manually forge for now, need sdk native tool bin support
    genmetata = find_program("genmetadata", Path(path.staging_dir, path.rel_prefix, "bin"))
    cmdline = [
        genmetata,
        "-o",
        str(output.resolve()),
        f"{json.dumps(metadata)}",
    ]
    subprocess.run(cmdline, check=True)


def run_gen_task_metadata_bin(input: Path, output: Path, path: ProjectPath) -> None:
    # Package metadata supports only string, convert package meta to task meta and generates blob
    elf = AppElf(str(input.resolve()), None)
    task_metadata = elf.get_package_metadata("task")

    task_metadata["version"] = 1

    # XXX: fix task.kconfig
    if "magic_value" in task_metadata.keys():
        task_metadata["magic"] = task_metadata["magic_value"]
        task_metadata.pop("magic_value")

    job_flags = []
    for flag in ["auto_start", "exit"]:
        f = next((k for k in task_metadata.keys() if flag in k), None)
        if f is not None:
            job_flags.append(f)

    task_metadata["flags"] = job_flags
    [task_metadata.pop(key, None) for key in job_flags]

    for entry in ["heap_size", "stack_size", "label", "magic"]:
        task_metadata[entry] = int(task_metadata[entry], base=16)

    for entry in ["priority", "quantum"]:
        task_metadata[entry] = int(task_metadata[entry], base=10)

    task_metadata["s_text"], text_size = elf.get_section_info(".text")
    _, ARM_size = elf.get_section_info(".ARM")
    task_metadata["text_size"] = align_to(text_size, 4) + align_to(ARM_size, 4)
    task_metadata["s_got"], task_metadata["got_size"] = elf.get_section_info(".got")

    task_metadata["s_svcexchange"], _ = elf.get_section_info(".svcexchange")
    _, task_metadata["data_size"] = elf.get_section_info(".data")
    _, task_metadata["bss_size"] = elf.get_section_info(".bss")

    task_metadata["entrypoint_offset"] = elf.get_symbol_offset_from_section("_start", ".text")
    # TODO
    task_metadata["domain"] = 0
    task_metadata["rodata_size"] = 0
    # task_metadata["finalize_offset"] = elf.get_symbol_offset_from_section("_exit", ".text")
    task_metadata["finalize_offset"] = 0

    task_metadata["num_devs"] = len(task_metadata["devs"])
    task_metadata["shms"] = []
    task_metadata["num_shms"] = len(task_metadata["shms"])
    task_metadata["dmas"] = []
    task_metadata["num_dmas"] = len(task_metadata["dmas"])

    task_metadata["task_hmac"] = []
    task_metadata["metadata_hmac"] = []

    _gen_metadata(output, {"task_meta": task_metadata}, path)


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("output", type=Path, help="output elf file")
    parser.add_argument("input", type=Path, help="partially linked input elf")
    parser.add_argument(
        "projectdir",
        type=Path,
        action="store",
        default=os.getcwd(),
        nargs="?",
        help="top level project directory",
    )
    parser.add_argument(
        "--prefix", type=str, default=os.path.join("usr", "local"), help="install staging prefix"
    )

    return parser


def run(argv: T.List[str]) -> None:
    args = argument_parser().parse_args(argv)
    # XXX: use builddir as option
    run_gen_task_metadata_bin(
        args.input, args.output, ProjectPath.load(args.projectdir / "output" / "build")
    )
