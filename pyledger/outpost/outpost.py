# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: LicenseRef-LEDGER

# XXX:
# tomllib is the standard buildt-in toml library since python 3.11
# prior to 3.11, use tomli instead (reference implementation that became the standard).
try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib

import os
import logging
from . import logger  # type: ignore
from .package import Package
from .buildsys import ninja_backend


class Project:
    def __init__(self, toml_filename: os.PathLike | str) -> None:
        assert isinstance(toml_filename, os.PathLike) or isinstance(
            toml_filename, str
        ), "argument must be a PathLike or str"

        self._topdir = os.path.dirname(os.path.abspath(toml_filename))
        self._sourcedir = os.path.join(self.topdir, "src")
        self._builddir = os.path.join(self.topdir, "build")
        self._stagingdir = os.path.join(self.topdir, "staging")

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
        ninja.add_meson_rules()
        for p in self._packages:
            ninja.add_meson_package(p)
        ninja.close()


def download(project: Project) -> None:
    project.download()


def setup(project: Project) -> None:
    project.setup()


def main():
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

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.ERROR)
    else:
        lvl = logging.getLevelName(args.log_level.upper())
        logger.setLevel(lvl)

    project = Project("project.toml")
    args.func(project)
