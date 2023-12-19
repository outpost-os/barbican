# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import lief
import os
import json
import codecs

from pyledger.outpost import logger

class Elf:
    SECTION_HEADER_SIZE = 16

    def __init__(self, elf: str, out: str) -> None:
        self._name = os.path.basename(elf)
        logger.info(f"Parsing {self.name} from {elf}")
        self._elf = lief.parse(elf)
        self._output_path = out
        if self._elf.has_section(section_name=".note.package"):
            logger.debug("package metadata section found")
            raw_data = self._elf.get_section(".note.package").content[Elf.SECTION_HEADER_SIZE:]
            self._package_metadata = json.loads(codecs.decode(bytes(raw_data), 'utf-8').strip('\x00'))
        else:
            self._package_metadata = None

    @property
    def name(self) -> str:
        return self._name

    def save(self) -> None:
        logger.info(f"Wrinting {self.name} to {self._output_path}")
        self._elf.write(self._output_path)

    @property
    def is_an_outpost_application(self) -> bool:
        if self._package_metadata is not None:
            return self._package_metadata["type"] == "outpost application"
        return False

    def get_section_info(self, section_name: str) -> (int,int):
        if not self._elf.has_section(section_name=section_name):
            raise ValueError

        section = self._elf.get_section(section_name)
        vma = section.virtual_address
        size = section.size
        return (vma, size)

    def get_symbol_address(self, symbol_name: str):
        if not self._elf.has_symbol(symbol_name):
            raise ValueError
        return self._elf.get_symbol(symbol_name).value

    def get_symbol_offset_from_section(self, symbol_name: str, from_section_name: str):
        section_vma, _ = self.get_section_info(from_section_name)
        sym_vma = self.get_symbol_address(symbol_name)
        return sym_vma - section_vma


class AppElf(Elf):
    # Section to relocate
    FLASH_SECTIONS = [ ".text", ".ARM" ]
    RAM_SECTIONS = [ ".svcexchange", ".got", ".data", ".bss" ]

    def __init__(self, elf: str, out: str) -> None:
        """Initialize an Outpost application Elf representation

        Parameters
        ----------
        elf : str
            Input elf file to parse
        out : str
            Path to written elf file while write method is called

        Exceptions
        ----------
        ValueError if the package metadata 'type' is not 'outpost application'
        """
        super().__init__(elf, out)
        if not self.is_an_outpost_application:
            raise ValueError

        self._prev_sections = dict()

        for section in *AppElf.FLASH_SECTIONS, *AppElf.RAM_SECTIONS:
            self._prev_sections[section] = self.get_section_info(section)

    @property
    def flash_size(self) -> int:
        flash_size = 0
        for section in AppElf.FLASH_SECTIONS:
            _, size = self.get_section_info(section)
            flash_size = flash_size + size
        return flash_size

    @property
    def ram_size(self) -> int:
        ram_size = \
            int(self._package_metadata["task"]["stack_size"], base=16) + \
            int(self._package_metadata["task"]["heap_size"], base=16)
        for section in AppElf.RAM_SECTIONS:
            _, size = self.get_section_info(section)
            ram_size = ram_size + size
        return ram_size

    def relocate(self, srom, sram):

        def _relocate_sections(sections, saddr):
            next_saddr = saddr
            for section_name in sections:
                section = self._elf.get_section(section_name)
                logger.debug(f"relocating {section_name}: {section.virtual_address:02x} -> {next_saddr:02x}")
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
            data_section.segments[0].physical_address = self.get_symbol_address('_sigot')

        def _symtab_fixup():
            """ Fixup symtab with relocated addresses"""

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
            """GoT fixup with relocated addresses"""
            s_ram = self._prev_sections[".svcexchange"][0]
            e_ram = self._elf.get_symbol("_sheap").value
            ram_offset = self._elf.get_section(".svcexchange").virtual_address - s_ram
            got = self._elf.get_section(".got")
            chunk_size = 4
            patched_got = bytearray()

            for i in range(0, len(got.content), chunk_size):
                addr = int.from_bytes(got.content[i:i+chunk_size], "little")
                if s_ram <= addr <= e_ram:
                    logger.debug(f"patching got entry {(got.virtual_address + i):02x}: {addr:02x} -> {(addr + ram_offset):02x}")
                    addr = addr + ram_offset
                patched_got += addr.to_bytes(chunk_size, "little")

            got.content = patched_got



        logger.info(f"relocating {self.name}")

        _relocate_sections(AppElf.FLASH_SECTIONS, srom)
        _relocate_sections(AppElf.RAM_SECTIONS, sram)
        _symtab_fixup()
        _got_fixup()
        _segment_fixup()
