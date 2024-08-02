# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, field, asdict
from enum import unique, auto
from functools import lru_cache
import json
from pathlib import Path
from typing import ClassVar

from . import StrEnum
from ..console import console


@unique
class DirName(StrEnum):
    Bin = auto()
    Build = auto()
    Configs = auto()
    Dts = auto()
    Host = auto()
    Images = auto()
    Include = auto()
    Lib = auto()
    Man = auto()
    Outpost_Private = auto()
    PkgConfig = auto()
    Share = auto()
    Src = auto()
    Sysroot = auto()
    Target = auto()


def default_prefix() -> Path:
    r"""Return default prefix according to build platform.

    Returns
    -------
    Path
        Build machine specific default prefix path.
        `C:\\` for Windows (except WSL) build machine
        `/usr/local` for posix like (any linuxes, WSL, macOS) build machine

    Notes
    -----
        This path is absolute
    """
    import os

    if os.name == "nt":
        return Path("C:/")
    else:
        return Path("/usr/local")


@dataclass(kw_only=True, frozen=True)
class ProjectPath:
    project_dir: Path
    output_dir: Path
    prefix: Path = field(default_factory=default_prefix)

    # ClassVar annotation is used by dataclass decorator in order to exclude member
    # from consideration as a field and to be ignored by the dataclass mechanisms.
    filename: ClassVar[str] = "project_tree.json"
    config_filename: ClassVar[str] = "project.toml"

    def __post_init__(self) -> None:
        if not self.prefix.is_absolute():
            # XXX: TODO use dedicated exception
            raise ValueError("prefix must be an absolute path")

        # Convert projectdir and outputdir to canonical path
        #  projectdir **must** exists
        #  outputdir **may** not had been created yet

        # XXX:
        #  As the dataclass is frozen, `__setattr__` method is deleted from generated class.
        #  One needs to use object base class `__setattr__` to (post)initialize the instance.
        #  This is only allowed in `__init__` and `__post_init__` methods.
        object.__setattr__(self, "project_dir", self.project_dir.resolve(strict=True))
        object.__setattr__(self, "output_dir", self.output_dir.resolve(strict=False))
        # XXX: check if config filename, configs and dts dir exist

    @staticmethod
    def asdict_factory(keyvals) -> dict:
        return {k: str(v) for k, v in keyvals}

    @classmethod
    def from_dict(cls, keyvals: dict) -> "ProjectPath":
        kwargs = {k: Path(v) for k, v in keyvals.items()}
        return cls(**kwargs)

    def save(self) -> None:
        """Save project path as a json file in project private build dir."""
        data = asdict(self, dict_factory=self.asdict_factory)
        with self.save_full_path.open("w") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load(cls, build_dir: Path) -> "ProjectPath":
        """Load project path for a given builddir from json."""
        try:
            file = (build_dir / DirName.Outpost_Private.value / cls.filename).resolve(strict=True)
        except FileNotFoundError:
            # XXX: dedicated error
            console.critical(f"{cls.filename} not found, please try to re run [i]setup[/i] command")
            raise
        with file.open("r") as f:
            data = json.load(f)
            return cls.from_dict(data)

    @property
    @lru_cache
    def config_full_path(self) -> Path:
        return self.project_dir / self.config_filename

    @property
    @lru_cache
    def save_full_path(self) -> Path:
        return self.private_build_dir / self.filename

    @property
    @lru_cache
    def configs_dir(self) -> Path:
        return self.project_dir / DirName.Configs.value

    @property
    @lru_cache
    def dts_dir(self) -> Path:
        return self.project_dir / DirName.Dts.value

    @property
    @lru_cache
    def rel_prefix(self) -> Path:
        return Path(*self.prefix.parts[1:])

    @property
    @lru_cache
    def build_dir(self) -> Path:
        return self.output_dir / DirName.Build.value

    @property
    @lru_cache
    def src_dir(self) -> Path:
        return self.output_dir / DirName.Src.value

    @property
    @lru_cache
    def host_dir(self) -> Path:
        return self.output_dir / DirName.Host.value

    @property
    @lru_cache
    def target_dir(self) -> Path:
        return self.output_dir / DirName.Target.value

    @property
    @lru_cache
    def sysroot_dir(self) -> Path:
        return self.output_dir / DirName.Sysroot.value

    @property
    @lru_cache
    def staging_dir(self) -> Path:
        # XXX: to be removed
        return self.output_dir / "staging"

    @property
    @lru_cache
    def images_dir(self) -> Path:
        return self.output_dir / DirName.Images.value

    @property
    @lru_cache
    def private_build_dir(self) -> Path:
        return self.build_dir / DirName.Outpost_Private.value

    @property
    @lru_cache
    def target_bin_dir(self) -> Path:
        # TODO: change to target dir, for compat (and temp) only, To Be Fixed later
        return self.staging_dir / self.rel_prefix / DirName.Bin.value

    @property
    @lru_cache
    def sysroot_lib_dir(self) -> Path:
        # TODO: change to sysroot dir, for compat (and temp) only, To Be Fixed later
        return self.staging_dir / self.rel_prefix / DirName.Lib.value

    @property
    @lru_cache
    def sysroot_pkgconfig_dir(self) -> Path:
        return self.sysroot_lib_dir / DirName.PkgConfig.value

    @property
    @lru_cache
    def sysroot_data_dir(self) -> Path:
        # TODO: change to sysroot dir, for compat (and temp) only, To Be Fixed later
        return self.staging_dir / self.rel_prefix / DirName.Share.value

    def mkdirs(self, exist_ok: bool = True) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=exist_ok)
        self.build_dir.mkdir(exist_ok=exist_ok)
        self.src_dir.mkdir(exist_ok=exist_ok)
        self.host_dir.mkdir(exist_ok=exist_ok)
        self.target_dir.mkdir(exist_ok=exist_ok)
        self.sysroot_dir.mkdir(exist_ok=exist_ok)
        # XXX: staging to be removed
        #  need to separate host tools from target devel (sdk/sysroot) and target install
        self.staging_dir.mkdir(exist_ok=exist_ok)
        self.images_dir.mkdir(exist_ok=exist_ok)
        self.private_build_dir.mkdir(exist_ok=exist_ok)
