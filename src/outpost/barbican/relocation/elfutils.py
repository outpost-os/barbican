# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import lief
import os
import json
import codecs

import typing

from ..logger import logger
from ..console import console


class Elf:
    SECTION_HEADER_SIZE = 16

    def __init__(self, elf: str, out: typing.Optional[str]) -> None:
        self._name: str = os.path.basename(elf)
        logger.info(f"Parsing {self.name} from {elf}")
        self._elf = typing.cast(lief.ELF.Binary, lief.parse(elf))
        self._output_path = out
        if self._elf.has_section(section_name=".note.package"):
            logger.debug("package metadata section found")
            raw_data = self._elf.get_section(".note.package").content[Elf.SECTION_HEADER_SIZE :]
            self._package_metadata = json.loads(
                codecs.decode(bytes(raw_data), "utf-8").strip("\x00")
            )
        else:
            self._package_metadata = None

    @property
    def name(self) -> str:
        return self._name

    def save(self) -> None:
        # XXX: FIXME
        logger.info(f"Wrinting {self.name} to {self._output_path}")
        self._elf.write(self._output_path)  # type: ignore

    @property
    def is_an_outpost_application(self) -> bool:
        if self._package_metadata is not None:
            return self._package_metadata["type"] == "outpost application"
        return False

    def get_section_info(self, section_name: str) -> tuple[int, int]:
        if not self._elf.has_section(section_name=section_name):
            raise ValueError

        section = self._elf.get_section(section_name)
        vma = section.virtual_address
        size = section.size
        return (vma, size)

    def get_symbol_address(self, symbol_name: str) -> int:
        if not self._elf.has_symbol(symbol_name):
            raise ValueError
        return self._elf.get_symbol(symbol_name).value

    def get_symbol_offset_from_section(self, symbol_name: str, from_section_name: str) -> int:
        section_vma, _ = self.get_section_info(from_section_name)
        sym_vma = self.get_symbol_address(symbol_name)
        return sym_vma - section_vma

    def get_package_metadata(self, *args: typing.Any) -> typing.Any:
        def _get_package_metadata(node: dict, *args: typing.Any) -> typing.Any:
            if len(args) == 1:
                return node[args[0]]
            else:
                key, *others = args
                node = node[key]
                return _get_package_metadata(node, *others)

        return _get_package_metadata(self._package_metadata, *args)


class SentryElf(Elf):
    FLASH_SECTIONS = [".isr_vector", ".task_list", ".text", ".ARM"]
    RAM_SECTIONS = [".bss", "._stack"]

    def __init__(self, elf: str, out: typing.Optional[str]) -> None:
        super().__init__(elf, out)

    def patch_task_list(self, task_meta_table: bytearray) -> None:
        tbl = self._elf.get_section(".task_list")
        task_meta_table.extend(bytes([0] * (tbl.size - len(task_meta_table))))
        assert len(task_meta_table) == tbl.size
        tbl.content = memoryview(task_meta_table)

    @property
    def flash_size(self) -> int:
        flash_size = 0
        for section in self.FLASH_SECTIONS:
            _, size = self.get_section_info(section)
            flash_size = flash_size + size
        return flash_size

    @property
    def ram_size(self) -> int:
        ram_size = 0
        for section in self.RAM_SECTIONS:
            _, size = self.get_section_info(section)
            ram_size = ram_size + size
        return ram_size


class AppElf(Elf):
    """Outpost application Elf representation.

    Attributes
    ----------
    FLASH_SECTIONS: list[str]
    RAM_SECTIONS: list[str]

    Parameters
    ----------
    elf: str
        Input elf file to parse
    out: str | None
        Path to written elf file while write method is called

    Raises
    ------
    ValueError
        Package metadata 'type' is not 'outpost application'
    """

    # Section to relocate
    FLASH_SECTIONS: list[str] = [".text", ".ARM"]
    RAM_SECTIONS: list[str] = [".svcexchange", ".got", ".data", ".bss"]

    def __init__(self, elf: str, out: str | None) -> None:
        super().__init__(elf, out)
        if not self.is_an_outpost_application:
            console.critical(f"{self.name} is not a valid outpost application")
            raise ValueError

        self._prev_sections = dict()

        for section in *AppElf.FLASH_SECTIONS, *AppElf.RAM_SECTIONS:
            self._prev_sections[section] = self.get_section_info(section)

    @property
    def flash_size(self) -> int:
        stext = self.get_symbol_address("_stext")
        erom = self.get_symbol_address("_erom")
        return erom - stext

    @property
    def stack_size(self) -> int:
        return int(self._package_metadata["task"]["stack_size"], base=16)

    @property
    def heap_size(self) -> int:
        return int(self._package_metadata["task"]["heap_size"], base=16)

    @property
    def ram_size(self) -> int:
        ram_size = self.stack_size + self.heap_size
        for section in AppElf.RAM_SECTIONS:
            _, size = self.get_section_info(section)
            ram_size = ram_size + size
        return ram_size

    def relocate(self, srom, sram):
        def _relocate_sections(sections, saddr):
            next_saddr = saddr
            for section_name in sections:
                section = self._elf.get_section(section_name)
                logger.debug(
                    f"relocating {section_name}: {section.virtual_address:02x} -> {next_saddr:02x}"
                )
                section.virtual_address = next_saddr
                next_saddr = next_saddr + section.size

        def _segment_fixup():
            text_section = self._elf.get_section(".text")
            text_section.segments[0].virtual_address = text_section.virtual_address
            text_section.segments[0].physical_address = text_section.virtual_address

            svc_section = self._elf.get_section(".svcexchange")
            svc_section.segments[0].virtual_address = svc_section.virtual_address
            svc_section.segments[0].physical_address = svc_section.virtual_address

            data_section = self._elf.get_section(".got")
            data_section.segments[0].virtual_address = data_section.virtual_address
            data_section.segments[0].physical_address = self.get_symbol_address("_sigot")

        def _symtab_fixup():
            """Fixup symtab with relocated addresses."""
            s_rom = self._prev_sections[".text"][0]
            e_rom = self._elf.get_symbol("_erom").value
            rom_offset = self._elf.get_section(".text").virtual_address - s_rom

            s_ram = self._prev_sections[".svcexchange"][0]
            e_ram = self._elf.get_symbol("_sheap").value
            ram_offset = self._elf.get_section(".svcexchange").virtual_address - s_ram

            for sym in self._elf.symbols:
                offset = 0
                if s_rom <= sym.value <= e_rom:
                    offset = rom_offset
                elif s_ram <= sym.value <= e_ram:
                    offset = ram_offset

                if offset > 0:
                    new_value = sym.value + offset
                    logger.debug(f"relocating {sym.name}: {sym.value:02x} -> {new_value:02x}")
                    sym.value = new_value

        def _got_fixup():
            """Got fixup with relocated addresses."""
            s_ram = self._prev_sections[".svcexchange"][0]
            e_ram = self._elf.get_symbol("_eheap").value
            ram_offset = self._elf.get_section(".svcexchange").virtual_address - s_ram
            got = self._elf.get_section(".got")
            chunk_size = 4
            patched_got = bytearray()

            for i in range(0, len(got.content), chunk_size):
                addr = int.from_bytes(got.content[i : i + chunk_size], "little")
                if s_ram <= addr <= e_ram:
                    logger.debug(
                        f"patching got entry {(got.virtual_address + i):02x}: {addr:02x} "
                        f"-> {(addr + ram_offset):02x}"
                    )
                    addr = addr + ram_offset
                patched_got += addr.to_bytes(chunk_size, "little")

            got.content = patched_got

        def _heap_fixup():
            _eheap_sym = self._elf.get_symbol("_eheap")
            _eheap_sym.value = _eheap_sym.value + self.heap_size

        logger.info(f"relocating {self.name}")
        logger.info(f" - flash start address {srom:#010x}")
        logger.info(f" - ram start address {sram:#010x}")

        _relocate_sections(AppElf.FLASH_SECTIONS, srom)
        _relocate_sections(AppElf.RAM_SECTIONS, sram)
        _symtab_fixup()
        _got_fixup()
        _segment_fixup()
        _heap_fixup()
        self._elf.header.entrypoint = self.get_symbol_address("_start")

    def remove_notes(self) -> None:
        for note_name in [".note.gnu.build-id", ".note.package"]:
            note_vma, _ = self.get_section_info(note_name)
            note_sym: lief.ELF.Symbol

            for sym in self._elf.symbols:
                if sym.value == note_vma:
                    note_sym = sym
                    break

            self._elf.remove_static_symbol(note_sym)
            self._elf.remove_section(note_name)

        # XXX
        # In symtab, each symbol section index is shift by 2 as we remove section
        # With note (which are at indices 1 and 2).
        # This is not robust and we need to look for the index of each sym's section
        # **but** this is not straight forward with lief.
        # We are doing it quick and dirty for demo purpose, an issue is added.
        for sym in self._elf.symbols:
            idx = sym.shndx
            idx = idx - 2 if idx > 0 else idx
            sym.shndx = idx

        # XXX
        # After removing note(s) symbol section
        # patch section offset in that segment
        for segment in self._elf.segments:
            if segment.type == lief.ELF.SEGMENT_TYPES.LOAD:
                offset = segment.file_offset
                print(offset)
                sections = segment.sections
                if sections and offset != sections[0].file_offset:
                    logger.debug("patching section offset in segment")
                    delta = sections[0].file_offset - offset
                    for section in sections:
                        offset = section.file_offset
                        # XXX
                        #  Some types seem to be lost, we probably need some additional hints
                        #  the `!r` only silents the type check error (i.e. str | bytes format in
                        #  log message)
                        logger.debug(
                            f" - section {section.name!r} offset: {offset:02x} -> "
                            f"{offset - delta:02x}"
                        )
                        section.file_offset = offset - delta
                    # XXX:
                    # left shift segment raw content from delta
                    # Even if section lma/vma are correct, data are fetched from file_offset
                    # in segment content, so we need to remove note data from the beginning of
                    # of that segment.
                    segment.content = segment.content[delta:]
