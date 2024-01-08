# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

# XXX:
# tomllib is the standard buildt-in toml library since python 3.11
# prior to 3.11, use tomli instead (reference implementation that became the standard).
try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib

import glob
import os
import logging
import pathlib

from . import logger  # type: ignore
from .package import Package
from .buildsys import ninja_backend
from .relocation import relocate_project


class Project:
    INSTALL_PREFIX = os.path.join("usr", "local")

    def __init__(self, toml_filename: os.PathLike | str) -> None:
        assert isinstance(toml_filename, os.PathLike) or isinstance(
            toml_filename, str
        ), "argument must be a PathLike or str"

        self._topdir = os.path.dirname(os.path.abspath(toml_filename))
        self._sourcedir = os.path.join(self.topdir, "src")
        self._builddir = os.path.join(self.topdir, "build")
        self._stagingdir = os.path.join(self.topdir, "staging")
        self._outdir = os.path.join(self.topdir, "out")


        with open(toml_filename, "rb") as f:
            self._toml = tomllib.load(f)

        logger.info(f"Outpost project '{self.name}'")
        logger.debug(f"project top level directory: {self.topdir}")
        logger.debug(f"project source directory: {self.sourcedir}")
        logger.debug(f"project build directory: {self.builddir}")
        logger.debug(f"project staging directory: {self.stagingdir}")

        os.makedirs(self.sourcedir, exist_ok=True)
        os.makedirs(self.builddir, exist_ok=True)
        os.makedirs(self.stagingdir, exist_ok=True)
        os.makedirs(self.outdir, exist_ok=True)

        self._packages = list()  # list of ABCpackage

        # Instantiate Sentry kernel
        self._packages.append(Package("sentry", self, self._toml["sentry"]))
        # Instantiate libshield
        self._packages.append(Package("libshield", self, self._toml["libshield"]))

        for app, node in self._toml["app"].items():
            self._packages.append(Package(app, self, node))

    @property
    def name(self) -> str:
        return self._toml["name"]

    @property
    def topdir(self) -> str:
        return self._topdir

    @property
    def sourcedir(self) -> str:
        return self._sourcedir

    @property
    def builddir(self) -> str:
        return self._builddir

    @property
    def stagingdir(self) -> str:
        return self._stagingdir

    @property
    def outdir(self) -> str:
        return self._outdir

    @property
    def bindir(self) -> str:
        return os.path.join(self.stagingdir, self.INSTALL_PREFIX, "bin")

    @property
    def libdir(self) -> str:
        return os.path.join(self.stagingdir, self.INSTALL_PREFIX, "lib")

    @property
    def datadir(self) -> str:
        return os.path.join(self.stagingdir, self.INSTALL_PREFIX, "share")

    def download(self) -> None:
        logger.info("Downloading packages")
        for p in self._packages:
            p.download()

    def update(self) -> None:
        logger.info("Updating packages")
        for p in self._packages:
            p.update()

    def setup(self) -> None:
        logger.info(f"Generating {self.name} Ninja build File")
        ninja = ninja_backend.NinjaGenFile(os.path.join(self.builddir, "build.ninja"))
        ninja.add_outpost_targets(self)
        ninja.add_meson_rules()
        for p in self._packages:
            ninja.add_meson_package(p)
        ninja.close()

    def relocate(self) -> None:
        relocate_project(self)
        # logger.info(f"{self.name} relocation")

        # sentry = None
        # idle = None
        # apps = list()

        # for elf in glob.glob(os.path.join(self.bindir, "*.elf")):
        #     name = os.path.basename(elf)
        #     if name == "sentry-kernel.elf":
        #         sentry = elfutils.Elf(elf, os.path.join(self.outdir, name))
        #     elif name == "idle.elf":
        #         idle = elfutils.Elf(elf, os.path.join(self.outdir, name))
        #     else:
        #         apps.append(elfutils.AppElf(elf, os.path.join(self.outdir, name)))

        # # Sort app list from bigger flash footprint to lesser
        # apps.sort(key=lambda x:x.flash_size, reverse=True)

        # # Beginning of user app flash and ram are after idle reserved memory in sentry kernel
        # idle_task_vma, idle_task_size = sentry.get_section_info(".idle_task")
        # idle_vma, idle_size = sentry.get_section_info("._idle")

        # next_task_srom = idle_task_vma + pow2_round_up(idle_task_size)
        # next_task_sram = idle_vma + pow2_round_up(idle_size)

        # for app in apps:
        #     app.relocate(next_task_srom, next_task_sram)
        #     next_task_srom = next_task_srom + pow2_round_up(app.flash_size)
        #     next_task_sram = next_task_sram + pow2_round_up(app.ram_size)
        #     app.save()

        # print(f"{apps[0].flash_size:02x}")
        # print(f"{apps[0].ram_size:02x}")

        # vma, size = app.get_section_info('.text')
        # print(f"vma {vma:02x}, size {size:02x}")
        # vma, size = app.get_section_info('.data')
        # print(f"vma {vma:02x}, size {size:02x}")
        # print(f"{app.get_symbol_address('_sidata'):02x}")
        # print(f"{app.get_symbol_offset_from_section('_sidata', '.text'):02x}")
        # XXX
        # get elf list, we must have, at least, sentry kernel and Idle
        # and apps. Do we assume one elf per app entry in toml, or is it possible
        # to have more than one elf ?

        # Parse all elf
        # Sort on text size
        # replace/align app
        # gen task_meta and kern fixup
        # make final bin

def download(project: Project) -> None:
    project.download()


def setup(project: Project) -> None:
    project.setup()


def relocate(project: Project) -> None:
    project.relocate()

def _main():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog="outpost", add_help=False)

    common_parser = ArgumentParser(add_help=False)
    loglevel_parser = common_parser.add_argument_group("logging")
    loglevel_parser.add_argument("-q", "--quiet", action="store_true")
    loglevel_parser.add_argument("-v", "--verbose", action="store_true")
    loglevel_parser.add_argument(
        "--log-level",
        action="store",
        choices=["debug", "info", "warning", "error"],
        default="info",
    )

    cmd_subparsers = parser.add_subparsers(required=True, help="command help")

    download_cmd_parser = cmd_subparsers.add_parser(
        "download", help="download help", parents=[common_parser]
    )
    download_cmd_parser.set_defaults(func=download)

    setup_cmd_parser = cmd_subparsers.add_parser(
        "setup", help="setup help", parents=[common_parser]
    )
    setup_cmd_parser.set_defaults(func=setup)
    setup_cmd_parser.add_argument("projectdir", type=pathlib.Path, action="store", default=os.getcwd(), nargs="?")

    relocate_cmd = cmd_subparsers.add_parser(
        "relocate", help="reloc help", parents=[common_parser]
    )
    relocate_cmd.set_defaults(func=relocate)
    relocate_cmd.add_argument("projectdir", type=pathlib.Path, action="store", default=os.getcwd(), nargs="?")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.ERROR)
    else:
        lvl = logging.getLevelName(args.log_level.upper())
        logger.setLevel(lvl)

    project = Project(os.path.join(args.projectdir, "project.toml"))
    args.func(project)


def main():
    try:
        _main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        exit(1)
    else:
        exit(0)
