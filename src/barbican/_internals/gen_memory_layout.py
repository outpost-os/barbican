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

from dts_utils import Dts

from ..relocation.elfutils import SentryElf, AppElf
from ..utils import memory_layout as memory
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


def _add_kernel_regions(layout: memory.Layout, sentry: SentryElf) -> None:
    text_start_addr, _ = sentry.get_section_info(".isr_vector")
    ram_start_addr, _ = sentry.get_section_info(".bss")
    # XXX: hardcoded name
    layout.append(
        memory.Region(
            name="kernel",
            type=memory.Region.Type.Text,  # type: ignore
            permission=memory.Region.Permission.Read | memory.Region.Permission.Exec,
            start_address=text_start_addr,
            size=sentry.flash_size,
        )
    )

    layout.append(
        memory.Region(
            name="kernel",
            type=memory.Region.Type.Ram,  # type: ignore
            permission=memory.Region.Permission.Read | memory.Region.Permission.Write,
            start_address=ram_start_addr,
            size=sentry.ram_size,
        )
    )


def _add_idle_regions(layout: memory.Layout, sentry: SentryElf) -> T.Tuple[int, int]:
    idle_text_saddr, idle_text_size = sentry.get_section_info(".idle_task")
    idle_ram_saddr, idle_ram_size = sentry.get_section_info("._idle")
    # XXX: hardcoded name
    layout.append(
        memory.Region(
            name="idle",
            type=memory.Region.Type.Text,  # type: ignore
            permission=memory.Region.Permission.Read | memory.Region.Permission.Exec,
            start_address=idle_text_saddr,
            size=idle_text_size,
        )
    )

    layout.append(
        memory.Region(
            name="idle",
            type=memory.Region.Type.Ram,  # type: ignore
            permission=memory.Region.Permission.Read | memory.Region.Permission.Write,
            start_address=idle_ram_saddr,
            size=idle_ram_size,
        )
    )

    return idle_text_saddr + idle_text_size, idle_ram_saddr + idle_ram_size


def _add_app_regions(
    layout: memory.Layout,
    app: AppElf,
    memory_slot: T.Tuple[int, int],
    code_limit: int,
    ram_limit: int,
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

    # XXX: dedicated error
    if flash_saddr + flash_size >= code_limit:
        raise Exception("task code region overflow")

    if ram_saddr + ram_size >= ram_limit:
        raise Exception("ram code region overflow")

    # trim extension
    name, _ = app.name.split(".", maxsplit=1)

    layout.append(
        memory.Region(
            name=name,
            type=memory.Region.Type.Text,  # type: ignore
            permission=memory.Region.Permission.Read | memory.Region.Permission.Exec,
            start_address=flash_saddr,
            size=flash_size,
        )
    )
    layout.append(
        memory.Region(
            name=name,
            type=memory.Region.Type.Ram,  # type: ignore
            permission=memory.Region.Permission.Read | memory.Region.Permission.Write,
            start_address=ram_saddr,
            size=ram_size,
        )
    )

    return flash_saddr + flash_size, ram_saddr + ram_size


def run_gen_memory_layout(output: Path, dts_filename: Path, exelist: list[Path]) -> None:
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
    dts_filename: Path
        dts file to use
    exelist: list[Path]
        list of executable path to consider

    Raises
    ------
    Exception if reserved memory for tasks code and/or ram is missing

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
    dts = Dts(dts_filename.resolve(strict=True))
    sentry, apps = _get_project_elves(exelist)

    layout = memory.Layout()
    _add_kernel_regions(layout, sentry)
    _add_idle_regions(layout, sentry)

    # TODO:
    #  Handle multiple bank
    reserved_memory = getattr(dts, "reserved-memory")
    if not reserved_memory:
        raise Exception("missing reserved memory node in dts file")

    tasks_code = reserved_memory.tasks_code
    tasks_ram = reserved_memory.tasks_ram

    if not tasks_code or not tasks_ram:
        raise Exception("missing applications reserved memory node in dts file")

    next_memory_slot = (tasks_code.reg[0], tasks_ram.reg[0])
    code_limit = tasks_code.reg[0] + tasks_code.reg[1]
    ram_limit = tasks_ram.reg[0] + tasks_ram.reg[1]

    for app in apps:
        next_memory_slot = _add_app_regions(layout, app, next_memory_slot, code_limit, ram_limit)

    layout.save(output)


def run_gen_dummy_memory_layout(output: Path) -> None:
    layout = memory.Layout()
    layout.append(
        memory.Region(
            name="dummy",
            type=memory.Region.Type.Text,  # type: ignore
            start_address=0x08000000,
            size=2 * 1024 * 1024,
        )
    )
    layout.append(
        memory.Region(
            name="dummy",
            type=memory.Region.Type.Ram,  # type: ignore
            start_address=0x20000000,
            size=2 * 1024 * 1024,
        )
    )

    layout.save(output)


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("output", type=Path, help="output filename")
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
        "--dts",
        type=Path,
        action="store",
        required=False,
        help="dts file to use for memory placement",
    )
    parser.add_argument(
        "-l",
        "--list",
        dest="exelist",
        action="extend",
        nargs="+",
        type=Path,
        required=False,
        help="List of executable to use for the firmware layout",
    )

    return parser


def run(argv: T.List[str]) -> None:
    """Execute memory_layout internal command."""
    args = argument_parser().parse_args(argv)

    if args.dummy:
        run_gen_dummy_memory_layout(args.output)
    elif args.exelist:
        run_gen_memory_layout(args.output, args.dts, args.exelist)
    else:
        # XXX: handle invalid command
        raise ValueError
        # run_gen_glob_memory_layout(args.output, args.projectdir, args.prefix)
