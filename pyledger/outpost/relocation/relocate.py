# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import glob
import os
import random

from .elfutils import Elf, AppElf, SentryElf
from .task_meta import TaskMeta, EXIT_MODES
from ..utils import pow2_round_up, align_to

from pyledger.outpost import logger  # type: ignore

def _get_project_elves(project):
    sentry = None
    idle = None
    apps = list()

    for elf in glob.glob(os.path.join(project.bindir, "*.elf")):
        name = os.path.basename(elf)
        if name == "sentry-kernel.elf":
            sentry = SentryElf(elf, os.path.join(project.outdir, name))
        elif name == "idle.elf":
            idle = Elf(elf, os.path.join(project.outdir, name))
        else:
            apps.append(AppElf(elf, os.path.join(project.outdir, name)))

    return sentry, idle, apps


def _relocate_apps(sentry, apps) -> None:
    # XXX:
    #  Need a smarter algorithm here
    #  Sort app by flash **AND** ram footprint w/ least padding order
    #  We may need to resize kernel + idle to ease memory relocation for application
    #  and keep one MPU region per app flash and ram region.
    #  Note this is for PMSAv7 only (power of 2, start addr align on size multiple),

    # Sort app list from bigger flash footprint to lesser
    apps.sort(key=lambda x:x.flash_size, reverse=True)

    # Beginning of user app flash and ram are after idle reserved memory in sentry kernel
    idle_task_vma, idle_task_size = sentry.get_section_info(".idle_task")
    idle_vma, idle_size = sentry.get_section_info("._idle")

    # next_task_srom = idle_task_vma + pow2_round_up(idle_task_size)
    # next_task_sram = idle_vma + pow2_round_up(idle_size)
    next_task_srom = idle_task_vma + (32*1024)
    next_task_sram = idle_vma + (32*1024)

    for app in apps:
        # In order to comply w/ PMSAv7
        #  - ceil size to a power of 2
        #  - and align start addr to that power of 2
        flash_size = pow2_round_up(app.flash_size)
        ram_size = pow2_round_up(app.ram_size)
        flash_saddr = align_to(next_task_srom, flash_size)
        ram_saddr = align_to(next_task_sram, ram_size)

        if flash_saddr != next_task_srom:
            logger.warning(f"MPU flash region misaligned, padded {flash_saddr - next_task_srom} bytes")

        if ram_saddr != next_task_sram:
            logger.warning(f"MPU flash region misaligned, padded {ram_saddr - next_task_sram} bytes")

        app.relocate(flash_saddr, ram_saddr)
        next_task_srom = flash_saddr + flash_size
        next_task_sram = ram_saddr + ram_size

def _generate_task_meta_table(apps) -> bytearray:
    task_meta_tbl = bytearray()

    for app in apps:
        meta = TaskMeta()
        meta.magic = int(app.get_package_metadata("task", "magic_value"), base=16)
        meta.version = 1
        meta.handle.id = random.getrandbits(16)
        meta.priority = int(app.get_package_metadata("task", "priority"), base=10)
        meta.quantum = int(app.get_package_metadata("task", "quantum"), base=10)
        meta.capabilities = 0 # XXX todo

        meta.flags.autostart_mode = bool(app.get_package_metadata("task", "auto_start"))

        for mode in EXIT_MODES:
            enabled = False
            try:
                enabled = bool(app.get_package_metadata("task", f"exit_{mode}"))
            except:
                pass
            finally:
                if enabled:
                    meta.flags.exit_mode = mode
                    break

        meta.domain = 0

        meta.s_text, text_size = app.get_section_info(".text")
        _, ARM_size = app.get_section_info(".ARM")
        meta.text_size = align_to(text_size, 4) + align_to(ARM_size, 4)
        print(f"{align_to(text_size, 4):#02x} + {align_to(ARM_size, 4):#02x} = {meta.text_size:#02x}")
        meta.s_got, meta.got_size = app.get_section_info(".got")
        #_, meta.rodata_size = app.get_section_info(".rodata") # XXX: rodata are included in .text section
        meta.s_svcexchange, _ = app.get_section_info(".svcexchange")
        _, meta.data_size = app.get_section_info(".data")
        _, meta.bss_size = app.get_section_info(".bss")
        meta.heap_size = int(app.get_package_metadata("task", "heap_size"), base=16)
        meta.stack_size = int(app.get_package_metadata("task", "stack_size"), base=16)

        meta.entrypoint_offset = app.get_symbol_offset_from_section("_start", ".text")
        # TODO
        # meta.finalize_offset = app.get_symbol_offset_from_section("_exit", ".text")

        # TODO all others fields
        #  - this will be done in the heavy tools in c/c++ (or Rust ?) for
        # consistency/maintainability/robustness reason (code duplication avoidance).

        task_meta_tbl.extend(meta.pack())

    return task_meta_tbl



def relocate_project(project) -> None:
    logger.info(f"{project.name} relocation")

    sentry, idle, apps = _get_project_elves(project)
    _relocate_apps(sentry, apps)
    task_meta_tbl = _generate_task_meta_table(apps)
    print(task_meta_tbl.hex(':'))
    sentry.patch_task_list(task_meta_tbl)

    sentry.save()
    idle.save()
    for app in apps:
        app.remove_notes()
        app.save()
