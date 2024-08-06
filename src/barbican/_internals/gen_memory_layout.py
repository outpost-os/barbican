# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

"""Memory layout internal command.

This internal command forge firmware memory layout for barbican applications.
"""

from argparse import ArgumentParser
import os
from pathlib import Path
import typing as T

from ..relocation.elfutils import SentryElf, AppElf
from ..utils.memory_layout import MemoryType, MemoryRegion, MemoryLayout
from ..utils.pathhelper import ProjectPath
from ..utils import align_to


def _get_project_elves(exelist: list[Path]) -> T.Tuple[SentryElf, T.List[AppElf]]:
    sentry: SentryElf
    apps: T.List[AppElf] = []

    for elf in exelist:
        name = elf.stem
        if name == "sentry-kernel":
            sentry = SentryElf(str(elf), None)
        elif name == "idle" or name == "autotest":
            continue
        else:
            apps.append(AppElf(str(elf), None))

    return sentry, apps


def _add_kernel_regions(layout: MemoryLayout, sentry: SentryElf) -> None:
    text_start_addr, _ = sentry.get_section_info(".isr_vector")
    ram_start_addr, _ = sentry.get_section_info(".bss")
    # XXX: hardcoded name
    layout.append(MemoryRegion("kernel", MemoryType.TEXT, text_start_addr, sentry.flash_size))
    layout.append(MemoryRegion("kernel", MemoryType.RAM, ram_start_addr, sentry.ram_size))


def _add_idle_regions(layout: MemoryLayout, sentry: SentryElf) -> T.Tuple[int, int]:
    idle_text_saddr, idle_text_size = sentry.get_section_info(".idle_task")
    idle_ram_saddr, idle_ram_size = sentry.get_section_info("._idle")
    # XXX: hardcoded name
    layout.append(MemoryRegion("idle", MemoryType.TEXT, idle_text_saddr, idle_text_size))
    layout.append(MemoryRegion("idle", MemoryType.RAM, idle_ram_saddr, idle_ram_size))

    return idle_text_saddr + idle_text_size, idle_ram_saddr + idle_ram_size


def _add_app_regions(
    layout: MemoryLayout, app: AppElf, memory_slot: T.Tuple[int, int]
) -> T.Tuple[int, int]:
    task_text, task_ram = memory_slot
    # TODO: round up according to target arch (i.e. armv7 -> pow2, armv8 -> 32 bytes)
    # flash_size = pow2_round_up(app.flash_size)
    # ram_size = pow2_round_up(app.ram_size)
    flash_size = align_to(app.flash_size, 32)
    ram_size = align_to(app.ram_size, 32)

    # TODO: only for armv7
    # flash_saddr = align_to(task_text, flash_size)
    # ram_saddr = align_to(task_ram, ram_size)
    flash_saddr = align_to(task_text, 32)
    ram_saddr = align_to(task_ram, 32)

    # trim extension
    name, _ = app.name.split(".", maxsplit=1)
    layout.append(MemoryRegion(name, MemoryType.TEXT, flash_saddr, flash_size))
    layout.append(MemoryRegion(name, MemoryType.RAM, ram_saddr, ram_size))

    return flash_saddr + flash_size, ram_saddr + ram_size


def run_gen_memory_layout(output: Path, exelist: list[Path]) -> None:
    """Memory layout internal command.

    This command does the barbican application memory placement in the dedicated memory pool.
    According to target architecture, each application is placed in memory in order to fit
    MPU region alignment and size.
    All applications must fit in target device RAM and Flash.
    This command outputs a memory layout json file.

    Parameters
    ----------
    output: Path
        output (in json) file path
    exelist: list[Path]
        list of executable path to consider

    Notes
    -----
      Idle and Autotest are special apps that are already placed in memory in a dedicated memory
      pool at kernel build time.

    .. warning:: Sentry kernel and applications must be built before calling this internal

    .. note:: generated memory layout json file is used as input the following internals:
      - :py:mod:`.relocate_elf` (PIC and/or prebuilt app)
      - :py:mod:`.plot_memory_layout`
      - :py:mod:`.gen_ldscript` (in case of noPIC w/ partially linked application)
    """
    sentry, apps = _get_project_elves(exelist)

    layout = MemoryLayout()
    _add_kernel_regions(layout, sentry)
    # FIXME: use application memory pool instead
    # This is not supported yet, applications are relocated right after idle task
    next_memory_slot = _add_idle_regions(layout, sentry)

    for app in apps:
        next_memory_slot = _add_app_regions(layout, app, next_memory_slot)

    layout.save_as_json(output)


def run_gen_glob_memory_layout(output: Path, projectdir: Path, prefix: Path) -> None:
    """Memory layout internal command.

    This command does the barbican application memory placement in the dedicated memory pool.
    According to target architecture, each application is placed in memory in order to fit
    MPU region alignment and size.
    All applications must fit in target device RAM and Flash.
    This command outputs a memory layout json file.

    Parameters
    ----------
    output: Path
        output (in json) file path
    projectdir: Path
        Project top level directory
    prefix: Path
        Install staging prefix

    Notes
    -----
      Idle and Autotest are special apps that are already placed in memory in a dedicated memory
      pool at kernel build time.

    .. warning:: Sentry kernel and applications must be built before calling this internal

    .. note:: generated memory layout json file is used as input the following internals:
      - :py:mod:`.relocate_elf` (PIC and/or prebuilt app)
      - :py:mod:`.plot_memory_layout`
      - :py:mod:`.gen_ldscript` (in case of noPIC w/ partially linked application)
    """
    path = ProjectPath.load(projectdir / "build")
    return run_gen_memory_layout(
        output, list((path.sysroot_dir / path.rel_prefix / "bin").glob("*.elf"))
    )


def run_gen_dummy_memory_layout(output: Path) -> None:
    layout = MemoryLayout()
    layout.append(MemoryRegion("dummy", MemoryType.TEXT, 0x08000000, 2 * 1024 * 1024))
    layout.append(MemoryRegion("dummy", MemoryType.RAM, 0x20000000, 2 * 1024 * 1024))
    layout.save_as_json(output)


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("output", help="output filename")
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
    parser.add_argument(
        "--dummy", action="store_true", required=False, help="generate a dummy layout"
    )
    parser.add_argument(
        "-l",
        "--list",
        dest="exelist",
        action="extend",
        nargs="+",
        type=Path,
        required=False,
        help="List of executable to use for the firmware layout,"
        "if empty, glob *.elf in staging dir",
    )

    return parser


def run(argv: T.List[str]) -> None:
    """Execute memory_layout internal command."""
    args = argument_parser().parse_args(argv)

    if args.dummy:
        run_gen_dummy_memory_layout(args.output)
    elif args.exelist:
        run_gen_memory_layout(args.output, args.exelist)
    else:
        run_gen_glob_memory_layout(args.output, args.projectdir, args.prefix)
