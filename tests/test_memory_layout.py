# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import dataclasses
import pytest
import typing

import barbican.utils.memory_layout as memory


class TestMemoryRegion:
    """MemoryRegion dataclass unittest.

    This dataclass is a keyword only, frozen dataclass.
    """

    _dict = {
        "name": "region1",
        "type": "ram",
        "permission": 1,
        "start_address": "0x8000000",
        "size": "0x400",
        "subregions": [],
    }

    @pytest.fixture(scope="class")
    def memory_region_file(self, tmp_path_factory):
        filename = tmp_path_factory.mktemp(type(self).__name__) / "memory_region.json"
        return filename

    @staticmethod
    def check_dataclass_field_types(region: memory.Region) -> bool:
        return all(
            isinstance(getattr(region, f.name), typing.get_origin(f.type) or f.type)
            for f in dataclasses.fields(region)
        )

    def test_default(self):
        # As a keyword only dataclass, must raises TypeError, no all default allowed
        with pytest.raises(TypeError):
            memory.Region()

    def test_positional_arguments(self):
        # As a keyword only dataclass, must raises TypeError, no positional arguments allowed
        with pytest.raises(TypeError):
            memory.Region("coucou", memory.Region.Type.Ram, memory.Region.Permission.Write, 42, 42)

    def test_keyword_arguments_int(self):
        region = memory.Region(
            name="coucou",
            type=memory.Region.Type.Ram,
            permission=memory.Region.Permission.Write,
            start_address=42,
            size=42,
        )

        assert dataclasses.is_dataclass(region)
        assert self.check_dataclass_field_types(region)
        assert region.name == "coucou"
        assert region.type == memory.Region.Type.Ram
        assert region.permission == memory.Region.Permission.Write
        assert region.start_address == 42
        assert region.size == 42
        assert len(region.subregions) == 0

    def test_keyword_arguments_hex_string(self):
        region = memory.Region(
            name="coucou",
            type=memory.Region.Type.Ram,
            permission=memory.Region.Permission.Write,
            start_address="0x42",
            size="0x42",
        )

        assert dataclasses.is_dataclass(region)
        assert self.check_dataclass_field_types(region)
        assert region.name == "coucou"
        assert region.type == memory.Region.Type.Ram
        assert region.permission == memory.Region.Permission.Write
        assert region.start_address == 0x42
        assert region.size == 0x42
        assert len(region.subregions) == 0

    @pytest.mark.dependency()
    def test_from_dict(self):
        region = memory.Region(**TestMemoryRegion._dict)
        assert dataclasses.is_dataclass(region)
        assert self.check_dataclass_field_types(region)

    @pytest.mark.dependency(depends=["TestMemoryRegion::test_from_dict"])
    def test_as_dict(self):
        region = memory.Region(**TestMemoryRegion._dict)
        assert (
            dataclasses.asdict(region, dict_factory=memory.Region.dict_factory)
            == TestMemoryRegion._dict  # noqa: W503
        )

    @pytest.mark.dependency(depends=["TestMemoryRegion::test_as_dict"])
    def test_save(self, memory_region_file):
        region = memory.Region(**TestMemoryRegion._dict)
        region.save(memory_region_file)

    @pytest.mark.dependency(depends=["TestMemoryRegion::test_save"])
    def test_load(self, memory_region_file):
        # as this test depends on test_save, and fixture scope is class
        # File must not be empty.
        assert memory_region_file.exists()
        region = memory.Region.load(memory_region_file)
        assert dataclasses.is_dataclass(region)
        assert self.check_dataclass_field_types(region)
        assert (
            dataclasses.asdict(region, dict_factory=memory.Region.dict_factory)
            == TestMemoryRegion._dict  # noqa: W503
        )
