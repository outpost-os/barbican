# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

# XXX:
# tomllib is the standard buildt-in toml library since python 3.11
# prior to 3.11, use tomli instead (reference implementation that became the standard).
try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib

from argparse import ArgumentParser
import os
import logging
import pathlib
import sys
import typing as T

from .console import console
from .logger import logger, log_config
from . import config
from .package import Package
from .buildsys import ninja_backend
from .utils import pathhelper


class Project:
    def __init__(self, project_dir: pathlib.Path) -> None:
        self.path = pathhelper.ProjectPath(
            project_dir=project_dir,
            output_dir=project_dir,
        )

        # XXX:
        #  Even if toml is a text format, the file must be opened as binary file
        with self.path.config_full_path.open("rb") as f:
            self._toml = tomllib.load(f)
            config.validate(self._toml)

        console.title(f"Barbican project '{self.name}'")

        self.path.mkdirs()
        self.path.save()

        self._packages = list()  # list of ABCpackage

        # XXX:
        # we assumed that the order in package list is fixed
        #  - 0: kernel
        #  - 1: libshield
        #  - 2..n: apps
        # There is only meson packages
        #
        # This will be, likely, false for next devel step.

        # Instantiate Sentry kernel
        self._packages.append(Package("sentry", self, self._toml["sentry"]))
        # Instantiate libshield
        self._packages.append(Package("libshield", self, self._toml["libshield"]))

        if "app" in self._toml:
            self._noapp = False
            for app, node in self._toml["app"].items():
                self._packages.append(Package(app, self, node, is_app=True))
        else:
            self._noapp = True

    @property
    def name(self) -> str:
        return self._toml["name"]

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
        ninja = ninja_backend.NinjaGenFile(os.path.join(self.path.build_dir, "build.ninja"))

        ninja.add_barbican_rules()
        ninja.add_barbican_internals_rules()
        ninja.add_barbican_targets(self)
        ninja.add_barbican_cross_file(pathlib.Path(self._toml["crossfile"]))
        dts_include_dirs = []
        for p in self._packages:
            dts_include_dirs.extend(p.dts_include_dirs)

        ninja.add_barbican_dts(
            (pathlib.Path(self.path.project_dir) / self._toml["dts"]).resolve(strict=True),
            dts_include_dirs,
        )

        ninja.add_meson_rules()

        # Add setup/compile/install targets for meson packages
        for p in self._packages:
            ninja.add_meson_package(p)

        if self._noapp:
            ninja.close()
            return

        # Dummy layout for dummy link
        dummy_layout = ninja.add_internal_gen_dummy_memory_layout_target(
            output=pathlib.Path(self.path.private_build_dir, "dummy_layout.json"),
        )

        # linkerscript template file
        # XXX: hardcoded in early steps
        linker_script_template = pathlib.Path(self._packages[1].data_dir) / "linkerscript.ld.in"

        dummy_linker_script = pathlib.Path(self.path.private_build_dir, "dummy.lds")
        ninja.add_gen_ldscript_target(
            "dummy", dummy_linker_script, linker_script_template, pathlib.Path(dummy_layout[0])
        )

        # Dummy link
        for app in self._packages[2:]:
            ninja.add_relink_meson_target(
                app.name,
                app.installed_exelist[0],
                app.dummy_linked_exelist[0],
                dummy_linker_script,
            )

        layout_sys_exelist = []
        layout_app_exelist = []
        for package in self._packages:
            if package.is_sys_package:
                layout_sys_exelist.extend(package.installed_exelist)
            else:
                layout_app_exelist.extend(package.dummy_linked_exelist)

        firmware_layout = ninja.add_internal_gen_memory_layout_target(
            output=pathlib.Path(self.path.private_build_dir, "layout.json"),
            dts=pathlib.Path(self.path.sysroot_data_dir, f"{pathlib.Path(self._toml['dts']).name}.pp"),
            dependencies=self._packages,
            sys_exelist=layout_sys_exelist,
            app_exelist=layout_app_exelist,
        )

        app_metadata = []
        app_hex_files = []

        # gen_ld/relink/gen_meta/objcopy app(s)
        for package in self._packages:
            if package.is_app_package:
                # XXX: Handle multiple exe package
                elf_in = package.installed_exelist[0]
                elf_out = package.relocated_exelist[0]
                linker_script = pathlib.Path(self.path.private_build_dir, f"{elf_in.stem}.lds")
                metadata_out = elf_out.with_suffix(".meta")
                hex_out = elf_out.with_suffix(".hex")

                ninja.add_gen_ldscript_target(
                    elf_in.stem,
                    linker_script,
                    linker_script_template,
                    pathlib.Path(firmware_layout[0]),
                    package.name,
                )
                ninja.add_relink_meson_target(
                    package.name,
                    elf_in,
                    elf_out,
                    linker_script,
                    package.name,
                )

                ninja.add_objcopy_rule(elf_out, hex_out, "ihex", [], package.name)
                app_hex_files.append(hex_out)

                ninja.add_gen_metadata_rule(
                    elf_out, metadata_out, pathlib.Path(self.path.project_dir)
                )
                app_metadata.append(metadata_out)

        # Patch kernel/objcopy
        kernel_elf = self._packages[0].installed_exelist[1]
        kernel_patched_elf = self._packages[0].relocated_exelist[1]
        kernel_hex = kernel_patched_elf.with_suffix(".hex")
        # idle_elf = self._packages[0].installed_exelist[0]
        # XXX this is ugly (...)
        idle_hex = self._packages[0].installed_exelist[0].with_suffix(".hex")

        ninja.add_fixup_kernel_rule(kernel_elf, kernel_patched_elf, app_metadata)
        ninja.add_objcopy_rule(kernel_patched_elf, kernel_hex, "ihex", [], self._packages[0].name)

        # XXX:
        # idle does not need to be relocated nor patched, use the one installed by sentry package
        # This is not a dependency of srec_cat as there is no explicit nor implicit rule to built-it
        # (this is an implicit **dynamic** output)
        # ninja.add_objcopy_rule(idle_elf, idle_hex, "ihex", None, self._packages[0].name)

        # srec_cat
        firmware_hex = pathlib.Path(self.path.build_dir) / "firmware.hex"
        ninja.add_srec_cat_rule(kernel_hex, idle_hex, app_hex_files, firmware_hex)

        ninja.close()


def download(project: Project) -> None:
    project.download()


def update(project: Project) -> None:
    project.update()


def setup(project: Project) -> None:
    project.setup()


def common_argument_parser() -> ArgumentParser:
    """Argument parser for logging infrastrucutre."""
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

    project_parser = common_parser.add_argument_group("project arguments")
    project_parser.add_argument(
        "projectdir", type=pathlib.Path, action="store", default=os.getcwd(), nargs="?"
    )

    return common_parser


def main_argument_parser() -> ArgumentParser:
    """Argument parser for main entrypoint."""
    parser = ArgumentParser(prog="barbican", add_help=True)
    common_parser = common_argument_parser()

    cmd_subparsers = parser.add_subparsers(
        required=True, title="Commands", dest="command", description="Execute one of the following"
    )

    # TODO: each command in a dedicated file w/ dedicate add_arg and run method
    download_cmd_parser = cmd_subparsers.add_parser(
        "download", help="download help", parents=[common_parser]
    )
    download_cmd_parser.set_defaults(func=download)

    update_cmd_parser = cmd_subparsers.add_parser(
        "update", help="update help", parents=[common_parser]
    )
    update_cmd_parser.set_defaults(func=update)

    setup_cmd_parser = cmd_subparsers.add_parser(
        "setup", help="setup help", parents=[common_parser]
    )
    setup_cmd_parser.set_defaults(func=setup)

    return parser


def run_command() -> None:
    """Run an barbican command."""
    args = main_argument_parser().parse_args()
    if args.verbose:
        log_config.set_console_log_level(logging.DEBUG)
    elif args.quiet:
        log_config.set_console_log_level(logging.ERROR)
    else:
        lvl = logging.getLevelName(args.log_level.upper())
        log_config.set_console_log_level(lvl)

    project = Project(args.projectdir)
    args.func(project)


def run_internal_command(cmd: str, argv: T.List[str]) -> None:
    """Run an internal barbican command.

    :param cmd: internal command name
    :type cmd: str
    :param argv: internal command arguments
    :type argv: List[str], optional

    Each internal commands are in the `_internal` subdir and each module is named with the
    command name. Each internal must accept an argument of type List[str].
    """
    import importlib

    module = importlib.import_module("barbican._internals." + cmd)
    module.run(argv)


def main() -> None:
    """Barbican script entrypoint.

    Execute an barbican command or an internal command.
    barbican commands are user entrypoint, dedicated help can be printed in terminal.
    barbican internal commands are used by build system backend for internal build steps,
    those are not available through user help.

    command usage:
     `barbican <cmd> [option(s)]`
    internal command usage:
     `barbican --internal <internal_cmd> [option(s)]`
    """
    try:
        if len(sys.argv) >= 2 and sys.argv[1] == "--internal":
            if len(sys.argv) == 2:
                raise ValueError("missing internal command")
            run_internal_command(sys.argv[2], sys.argv[3:])
        else:
            run_command()

    except Exception as e:
        logger.critical(str(e))
        raise
        exit(1)
    else:
        exit(0)
