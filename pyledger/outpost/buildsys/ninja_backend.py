# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import os
import ninja_syntax  # type: ignore

from pathlib import Path
from typing import TYPE_CHECKING


from ..utils.environment import find_program

if TYPE_CHECKING:
    from ..package import Package
    from ..outpost import Project


class NinjaGenFile:
    def __init__(self, filename):
        self._raw_file = open(filename, "w")
        self._ninja = ninja_syntax.Writer(self._raw_file)
        self._ninja.comment("Outpost build.ninja")
        self._ninja.comment("Auto generated file **DO NOT EDIT**")

        # self._add_common_variables()
        # self._add_outpost_rules()

    def close(self) -> None:
        """Close, and thus write to disk, ninja build file"""
        self._raw_file.close()

    # def _add_common_variables(self) -> None:
    #     self._ninja.newline()
    #     self._ninja.variable("ninjabuild", find_program("ninja"))
    #     self._ninja.variable("mesonbuild", find_program("meson"))
    #     self._ninja.variable("outpost", find_program("outpost"))
    #     self._ninja.variable("srec_cat", find_program("srec_cat"))
    #     # FIXME: get this from toml
    #     self._ninja.variable("crossfile", "arm-none-eabi-gcc.ini")

    def add_outpost_rules(self) -> None:
        self._ninja.newline()
        self._ninja.variable("outpost", find_program("outpost"))
        self._ninja.newline()
        self._ninja.rule(
            "outpost_reconfigure",
            description="outpost project reconfiguration",
            generator=True,
            command="$outpost setup $projectdir",
            pool="console",
        )

    def add_outpost_internals_rules(self) -> None:
        def _add_outpost_internal_rule(name: str, args: str) -> None:
            self._ninja.newline()
            self._ninja.rule(
                f"{name}",
                description=f"outpost internal {name} command",
                command=f"$outpost --internal {name} {args}",
                pool="console",
            )

        internal_commands = {
            "gen_memory_layout": "--prefix=$prefix $out $projectdir",
            "capture_out": "$out $cmdline",
            # TODO: complete list
        }

        for command, args in internal_commands.items():
            _add_outpost_internal_rule(command, args)

        # To be removed
        # self._ninja.rule(
        #     "outpost_relocation",
        #     description="outpost project relocation",
        #     command="$outpost relocate -v $projectdir",
        #     pool="console",
        # )

    def add_outpost_targets(self, project: "Project") -> None:
        self._ninja.newline()
        self._ninja.build(
            "build.ninja",
            "outpost_reconfigure",
            variables={"projectdir": project.topdir},
            implicit=os.path.join(project.topdir, "project.toml"),
        )

        # XXX:
        # may depends on actually installed elf instead of install target
        # may declare output correctly too.
        # This apply to all meson targets too
        # self._ninja.build(
        #     "relocate",
        #     "outpost_relocation",
        #     variables={"projectdir": project.topdir},
        #     implicit=[f"{package.name}_install" for package in project._packages],
        # )

    def add_internal_gen_memory_layout_target(
        self, output: Path, projectdir: Path | str, prefix: Path | str, dependencies: list
    ) -> list:
        self._ninja.newline()
        return self._ninja.build(
            str(output),
            "gen_memory_layout",
            variables={"projectdir": projectdir, "prefix": prefix},
            implicit=[f"{package.name}_install" for package in dependencies],
        )

    def add_meson_rules(self) -> None:
        self._ninja.newline()
        self._ninja.variable("mesonbuild", find_program("meson"))
        self._ninja.newline()
        # FIXME: get this from toml
        self._ninja.variable("crossfile", "arm-none-eabi-gcc.ini")
        self._ninja.newline()
        self._ninja.rule(
            "meson_setup",
            description="meson setup $name",
            command="$mesonbuild setup --cross-file=$crossfile $opts $builddir $sourcedir",
            pool="console",
        )
        self._ninja.newline()
        self._ninja.rule(
            "meson_compile",
            description="meson compile $name",
            pool="console",
            command="$mesonbuild compile -C $builddir",
        )
        self._ninja.newline()
        self._ninja.rule(
            "meson_install",
            description="meson install $name",
            pool="console",
            command="$mesonbuild install --only-changed --destdir $stagingdir -C $builddir",
        )

    def add_meson_package(self, package: "Package") -> None:
        self._ninja.newline()
        self._ninja.build(
            f"{package.builddir}/build.ninja",
            "meson_setup",
            variables={
                "builddir": package.builddir,
                "sourcedir": package.sourcedir,
                "name": package.name,
                "opts": package.build_opts,
            },
            implicit=[f"{dep}_install" for dep in package.deps],
        )
        self._ninja.newline()
        self._ninja.build(f"{package.name}_setup", "phony", f"{package.builddir}/build.ninja")
        self._ninja.newline()
        self._ninja.build(
            f"{os.path.join(package.parent.builddir, package.name)}_introspect.json",
            "capture_out",
            variables={
                "cmdline": f"$mesonbuild introspect --all -i -f --backend ninja {package.builddir}"
            },
        )
        self._ninja.newline()
        self._ninja.build(
            f"{package.name}_compile",
            "meson_compile",
            implicit=f"{package.name}_setup",
            variables={
                "builddir": package.builddir,
                "name": package.name,
            },
        )
        self._ninja.newline()
        self._ninja.build(
            f"{package.name}_install",
            "meson_install",
            f"{package.name}_compile",
            variables={
                "builddir": package.builddir,
                "name": package.name,
                "stagingdir": package.stagingdir,
            },
        )
        self._ninja.newline()
