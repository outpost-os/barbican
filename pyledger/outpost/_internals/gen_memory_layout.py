# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

""" Memory layout internal command

This internal command forge firmware memory layout for outpost applications.



"""

from argparse import ArgumentParser
import os
from pathlib import Path
import typing as T

from ..relocation.elfutils import SentryElf, AppElf
from ..utils.memory_layout import MemoryRegion, MemoryLayout
from ..utils.pathhelper import ProjectPathHelper
from ..utils import pow2_round_up, align_to


def _get_project_elves(bindir: Path) -> T.Tuple[SentryElf, T.List[AppElf]]:
    sentry: SentryElf
    apps: T.List[AppElf] = []

    for elf in bindir.glob("*.elf"):
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
    layout.append(MemoryRegion("kernel text", text_start_addr, sentry.flash_size))
    layout.append(MemoryRegion("kernel ram", ram_start_addr, sentry.ram_size))


def _add_idle_regions(layout: MemoryLayout, sentry: SentryElf) -> T.Tuple[int, int]:
    idle_text_saddr, idle_text_size = sentry.get_section_info(".idle_task")
    idle_ram_saddr, idle_ram_size = sentry.get_section_info("._idle")
    layout.append(MemoryRegion("idle text", idle_text_saddr, idle_text_size))
    layout.append(MemoryRegion("idle ram", idle_ram_saddr, idle_ram_size))

    return idle_text_saddr + idle_text_size, idle_ram_saddr + idle_ram_size


def _add_app_regions(
    layout: MemoryLayout, app: AppElf, memory_slot: T.Tuple[int, int]
) -> T.Tuple[int, int]:
    task_text, task_ram = memory_slot
    # TODO: round up according to target arch (i.e. armv7 -> pow2, armv8 -> 32 bytes)
    flash_size = pow2_round_up(app.flash_size)
    ram_size = pow2_round_up(app.ram_size)

    # TODO: only for armv7
    flash_saddr = align_to(task_text, flash_size)
    ram_saddr = align_to(task_ram, ram_size)

    layout.append(MemoryRegion(f"{app.name} text", flash_saddr, flash_size))
    layout.append(MemoryRegion(f"{app.name} ram", ram_saddr, ram_size))

    return flash_saddr + flash_size, ram_saddr + ram_size


def run_gen_memory_layout(output: Path, projectdir: Path, prefix: Path) -> None:
    """Memory layout internal command

    This command does the outpost application memory placement in the dedicated memory pool.
    According to target architecture, each application is placed in memory in order to fit
    MPU region alignment and size.
    All applications must fit in target device RAM and Flash.
    This command outputs a memory layout json file.

    Parameters
    ----------
    output
        output (in json) file path
    projectdir
        Project top level directory
    prefix
        Install staging prefix

    Notes
    -----
      Idle and Autotest are special apps that are already placed in memory in a dedicated memory
      pool at kernel build time.

    .. warning:: Sentry kernel and applications must be built before calling this internal

    .. note:: generated memory layout json file is used as input the following internals:
      - :py:mod:`.relocate_elf` (PIC and/or prebuilt app)
      - :py:mod:`.plot_memory_layout`
      - :py_mod:`.gen_ldscript` (in case of noPIC w/ partially linked application)
    """
    project = ProjectPathHelper(projectdir, prefix)
    sentry, apps = _get_project_elves(project.bindir)

    layout = MemoryLayout()
    _add_kernel_regions(layout, sentry)
    # FIXME: use application memory pool instead
    # This is not supported yet, applications are relocated right after idle task
    next_memory_slot = _add_idle_regions(layout, sentry)

    for app in apps:
        next_memory_slot = _add_app_regions(layout, app, next_memory_slot)

    layout.save_as_json(output)


def run(argv: T.List[str]) -> None:
    """Execute memory_layout internal command"""
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
    args = parser.parse_args(argv)
    run_gen_memory_layout(args.output, args.projectdir, args.prefix)
