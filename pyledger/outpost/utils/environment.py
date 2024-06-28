# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import logging
import shutil
import typing as T
from pathlib import Path

# XXX:
# tomllib is the standard buildt-in toml library since python 3.11
# prior to 3.11, use tomli instead (reference implementation that became the standard).
try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib

from ..config import validate as config_schema_validate
from ..logger import logger


_PROGRAM_CACHE_DICT: dict[str | bytes, str | bytes] = {}


@T.overload
def find_program(name: str) -> str: ...
@T.overload
def find_program(name: bytes) -> bytes: ...
@T.overload
def find_program(name: str, path: T.Optional[Path]) -> str: ...
@T.overload
def find_program(name: bytes, path: T.Optional[Path]) -> bytes: ...


def find_program(name: str | bytes, path: T.Optional[Path] = None) -> str | bytes:
    if name not in _PROGRAM_CACHE_DICT.keys():
        log = f"Find Program: {name!r}"
        if path:
            log += f" (alt. path: {path})"
        cmd = shutil.which(name, path=path)
        log += ": OK" if cmd else ": NOK"
        log_level = logging.INFO if cmd else logging.ERROR
        logger.log(log_level, log)

        if not cmd:
            raise Exception("Required program not found")

        _PROGRAM_CACHE_DICT[name] = cmd

    return _PROGRAM_CACHE_DICT[name]


class Environment:
    # private build and cache dir
    _private_builddir = Path("build.private")
    _cachedir = Path("build.cache")
    # TODO log ?

    # Next dirs follows FHS v3.0 specification
    # Those are relpath relative to target, sysroot or host devel root directory
    _bindir = Path("bin")
    _includedir = Path("include")
    _libdir = Path("lib")
    _pkgconfigdir = Path(_libdir, "pkgconfig")
    _datadir = Path("share")
    _mandir = Path("man")

    def __init__(self, config_filename: Path, output_dir: Path) -> None:
        # First of all, make sure that project configuration file exists and its valid
        self._config_filename: Path = config_filename.resolve(strict=True)
        with open(self._config_filename, "rb") as f:
            self._config = tomllib.load(f)
            config_schema_validate(self._config)

        # Check project layout compliance
        self._topdir: Path = self._config_filename.parent
        self._configsdir: Path = Path(self.topdir, "configs").resolve(strict=True)

        # XXX: list of dts include dirs
        # to be fixed later
        self._dtsdir: list[Path] = [Path(self.topdir, "dts").resolve(strict=True)]

        # Create output layout
        self._outputdir: Path = output_dir
        self._builddir: Path = Path(self.outputdir, "build")
        self._srcdir: Path = Path(self.outputdir, "src")
        self._hostdir: Path = Path(self.outputdir, "host")
        self._targetdir: Path = Path(self.outputdir, "target")
        self._sysrootdir: Path = Path(self.outputdir, "sysroot")
        self._imagesdir: Path = Path(self.outputdir, "images")

        self._prefix: Path = Path(self._config.get("prefix", "usr/local"))
        # if prefix is absolute, remove root (`/` or `C:\\`) as prefix applied from
        # (sys)root and not devel machine root
        # E.g. lib path while building or in SDK
        #  <outdir>/<sysroot>/<prefix>/lib
        # or
        #  <sdk>/<target_sysroot>/<prefix>/lib
        if self._prefix.is_absolute():
            self._prefix = Path(*self._prefix.parts[1:])

    @property
    def topdir(self) -> Path:
        return self._topdir

    @property
    def configsdir(self) -> Path:
        return self._configsdir

    @property
    def dtsdir(self) -> list[Path]:
        return self._dtsdir

    @property
    def outputdir(self) -> Path:
        return self._outputdir

    @property
    def builddir(self) -> Path:
        return self._builddir

    @property
    def srcdir(self) -> Path:
        return self._srcdir

    @property
    def hostdir(self) -> Path:
        return self._hostdir

    @property
    def targetdir(self) -> Path:
        return self._targetdir

    @property
    def sysrootdir(self) -> Path:
        return self._sysrootdir

    @property
    def imagesdir(self) -> Path:
        return self._imagesdir

    @property
    def cachedir(self) -> Path:
        return Path(self.builddir, self._cachedir)

    @property
    def privatedir(self) -> Path:
        return Path(self.builddir, self._private_builddir)

    def create_outputdir_layout(self) -> None:
        self.outputdir.mkdir(parents=True, exist_ok=True)
        self.builddir.mkdir(parents=True, exist_ok=True)
        self.srcdir.mkdir(parents=True, exist_ok=True)
        self.hostdir.mkdir(parents=True, exist_ok=True)
        self.targetdir.mkdir(parents=True, exist_ok=True)
        self.sysrootdir.mkdir(parents=True, exist_ok=True)
        self.imagesdir.mkdir(parents=True, exist_ok=True)
        self.cachedir.mkdir(parents=True, exist_ok=True)
        self.privatedir.mkdir(parents=True, exist_ok=True)
