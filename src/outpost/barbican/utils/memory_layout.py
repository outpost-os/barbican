# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, fields, field, asdict
from enum import unique, auto, IntFlag

from enum import Enum
import json
from pathlib import Path
import typing as T

from . import StrEnum


@dataclass(kw_only=True, frozen=True)
class Region:
    @unique
    class Type(StrEnum):
        Text = auto()
        Ram = auto()

    @unique
    class Permission(IntFlag):
        Read = auto()
        Write = auto()
        Exec = auto()

    name: str
    type: Type
    permission: Permission = Permission(0)
    start_address: int
    size: int
    subregions: T.List["Region"] = field(default_factory=list)

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            value_type = T.cast(type, f.type)
            if value_type is int and isinstance(value, str):
                object.__setattr__(self, f.name, int(value, 16))
            elif value_type is T.List["Region"] and all(isinstance(e, dict) for e in value):
                object.__setattr__(self, f.name, [Region(**e) for e in value])
            elif issubclass(value_type, Enum):
                object.__setattr__(self, f.name, value_type(value))

    @staticmethod
    def dict_factory(x):
        d = dict()
        for k, v in x:
            if isinstance(v, Enum):
                v = v.value
            elif isinstance(v, int):
                v = hex(v)

            d[k] = v

        return d

    @classmethod
    def from_dict(cls, keyvals: dict) -> "Region":
        return cls(**keyvals)

    def save(self, filepath: Path) -> None:
        data = asdict(self, dict_factory=self.dict_factory)
        with filepath.open("w") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load(cls, filepath: Path) -> "Region":
        with filepath.resolve(strict=True).open("r") as f:
            data = json.load(f)
            return cls.from_dict(data)


@dataclass
class Layout:
    """Memory Layout.

    Memory layout is a user defined list that can only accepts :py:class:`MemoryRegion` items.
    """

    regions: list[Region] = field(default_factory=list)

    def append(self, region: Region) -> None:
        self.regions.append(region)

    def save(self, filepath: Path) -> None:
        data = asdict(self, dict_factory=Region.dict_factory)
        with filepath.open("w") as f:
            json.dump(data, f, indent=4)

    # def load
