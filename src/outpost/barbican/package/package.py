# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
import collections.abc
from pathlib import Path

from functools import lru_cache
from enum import auto, unique

from ..console import console
from ..logger import logger
from ..scm import scm_create
from ..utils import StrEnum

import typing as T

if T.TYPE_CHECKING:
    from ..barbican import Project


@unique
class Backend(StrEnum):
    Cargo = auto()
    Meson = auto()


class BackendFactoryMap(collections.abc.Mapping[Backend, collections.abc.Callable]):
    def __init__(self) -> None:
        self._key_type = Backend

    def __len__(self):
        return len(self._key_type)

    def __iter__(self):
        yield from [k.value for k in list(self._key_type)]

    def __getitem__(self, key):
        method = self._key_type(key)

        from importlib import import_module
        import sys

        return getattr(
            import_module("." + method.value, sys.modules[__name__].__package__), method.name
        )


class Package(ABC):
    __backend_factories: T.ClassVar[BackendFactoryMap] = BackendFactoryMap()

    __built_in_options: T.ClassVar[list[str]] = [
        "static_pie",
    ]

    @unique
    class Type(StrEnum):
        """Package type enumerate."""

        Kernel = auto()
        """Package is the kernel (a.k.a. Sentry)"""

        Runtime = auto()
        """Package is the runtime library for a given language (e.g. libshield, shield-rs)"""

        Library = auto()
        """Package is a system wide library (other than runtime)"""

        Service = auto()
        """Package is a system service"""

        Application = auto()
        """Package is an user application"""

    def __init__(
        self,
        name: str,
        parent_project: "Project",
        config_node: dict,
        type: "Package.Type",  # type: ignore[arg-type]
    ) -> None:
        self._name = name
        self._type: Package.Type = type
        self._parent = parent_project
        self._config = config_node
        self._scm = scm_create(name, parent_project.path.src_dir, self._config)

        self._provides: list[str]
        if self._type == Package.Type.Kernel:
            self._provides = ["idle.elf", "sentry-kernel.elf"]
        else:
            self._provides = self._config["provides"] if "provides" in self._config.keys() else []

        self._dts_include_dirs = [Path(self.src_dir) / "dts"]
        if "extra_dts_incdir" in self._config:
            # extra dts includedir are source package relative
            self._dts_include_dirs.extend(
                [Path(self.src_dir) / d for d in self._config["extra_dts_incdir"]]
            )

        dotconfig = Path(self._config["config"])
        if dotconfig.is_absolute():
            # XXX proper execpetion handling
            raise Exception("config file must be project top level relative file")

        # XXX: Enforce path rel to project configs dir
        self._dotconfig = (Path(self._parent.path.project_dir) / dotconfig).resolve(strict=True)

        self._built_in_build_opts = dict()
        self._extra_build_opts = dict()
        if "build" in self._config:
            build_opts = (
                self._config["build"]["options"] if "options" in self._config["build"] else dict()
            )
            self._built_in_build_opts = dict(
                filter(lambda key: key in self.__built_in_options, build_opts.items())
            )
            self._extra_build_opts = dict(
                filter(lambda key: key not in self.__built_in_options, build_opts.items())
            )

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_application(self) -> bool:
        return self._type == Package.Type.Application

    @property
    def is_kernel(self) -> bool:
        return self._type == Package.Type.Kernel

    @property
    def is_runtime(self) -> bool:
        return self._type == Package.Type.Runtime

    @property
    def is_sys_package(self) -> bool:
        return self.is_kernel or self.is_runtime

    @property
    def backend(self) -> Backend:
        return Backend(self.__class__.__name__.lower())

    @property
    @lru_cache
    def src_dir(self) -> Path:
        return self._parent.path.src_dir / self.name

    @property
    @lru_cache
    def build_dir(self) -> Path:
        return self._parent.path.build_dir / self.name

    @property
    @lru_cache
    def staging_dir(self) -> Path:
        return self._parent.path.staging_dir

    @property
    @lru_cache
    def pkgconfig_dir(self) -> Path:
        return self._parent.path.sysroot_pkgconfig_dir

    @property
    @lru_cache
    def bin_dir(self) -> Path:
        return self._parent.path.target_bin_dir

    @property
    @lru_cache
    def lib_dir(self) -> Path:
        return self._parent.path.sysroot_lib_dir

    @property
    @lru_cache
    def data_dir(self) -> Path:
        return self._parent.path.sysroot_data_dir / self.name.replace("lib", "", 1)

    @property
    def built_targets(self) -> list[Path]:
        return [Path(self.build_dir) / exe for exe in self._provides]

    @property
    def installed_targets(self) -> list[Path]:
        return [Path(self.bin_dir) / exe for exe in self._provides]

    @property
    def dummy_linked_targets(self) -> list[Path]:
        dummy_list = []
        for exe in self._provides:
            exe_path = self._parent.path.private_build_dir / exe
            new_suffix = ".dummy" + exe_path.suffix
            dummy_list.append(exe_path.with_suffix(new_suffix))

        return dummy_list

    @property
    def relocated_targets(self) -> list[Path]:
        return [Path(self._parent.path.private_build_dir) / exe for exe in self._provides]

    @property
    def dts_include_dirs(self) -> list[Path]:
        return self._dts_include_dirs

    @property
    def parent(self):
        return self._parent

    @property
    def deps(self):
        if self._type == Package.Type.Kernel:
            return []
        elif self._type == Package.Type.Runtime:
            return [Package.Type.Kernel.value]
        else:
            deps = [Package.Type.Runtime.value]
            if "depends" in self._config:
                deps.extend(self._config["depends"])
            return deps

    @classmethod
    def get_backend_factory(cls, backend: str) -> T.Type["Package"]:
        return cls.__backend_factories[Backend(backend)]

    def download(self) -> None:
        logger.info(f"Downloading {self.name} from {self.url}")
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self._scm.download()

        # TODO post download trigger in config
        with console.status(f"Running {self.backend.name} post download hook"):
            self.post_download_hook()
        console.message("[b]Done.[/b]")

    def update(self) -> None:
        logger.info(f"Updating {self.name}")
        self._scm.update()

        # TODO post udpate trigger in config
        with console.status(f"Running {self.backend.name} post update hook"):
            self.post_update_hook()

    def __getattr__(self, attr):
        return self._config[attr] if attr in self._config else None

    @property
    @abstractmethod
    def build_options(self) -> list[str]: ...

    @abstractmethod
    def post_download_hook(self) -> None: ...

    @abstractmethod
    def post_update_hook(self) -> None: ...


def create_package(
    name: str, parent_project: "Project", config_node: dict, type: Package.Type
) -> Package:
    PackageCls = Package.get_backend_factory(config_node["build"]["backend"])
    return PackageCls(name, parent_project, config_node, type)
