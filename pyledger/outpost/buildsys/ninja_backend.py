# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

import os
import ninja_syntax  # type: ignore
from .external_program import external_programs_initialize, external_program_get

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyledger.outpost.package import Package
    from pyledger.outpost.outpost import Project


class NinjaGenFile:
    def __init__(self, filename):
        external_programs_initialize()
        self._raw_file = open(filename, "w")
        self._ninja = ninja_syntax.Writer(self._raw_file)
        self._ninja.comment("SPDX-License-Identifier: Apache-2.0")
        self._ninja.comment("Outpost build.ninja")
        self._ninja.comment("Auto generated file **DO NOT EDIT**")

        self._add_common_variables()
        self._add_outpost_rules()

    def close(self) -> None:
        """Close, and thus write to disk, ninja build file"""
        self._raw_file.close()

    def _add_common_variables(self) -> None:
        self._ninja.newline()
        self._ninja.variable("ninjabuild", external_program_get("ninja"))
        self._ninja.variable("mesonbuild", external_program_get("meson"))
        self._ninja.variable("outpost", external_program_get("outpost"))
        self._ninja.variable("srec_cat", external_program_get("srec_cat"))
        # FIXME: get this from toml
        self._ninja.variable("crossfile", "arm-none-eabi-gcc.ini")

    def _add_outpost_rules(self) -> None:
        self._ninja.newline()
        self._ninja.rule(
            "outpost_reconfigure",
            description="outpost project reconfiguration",
            generator=True,
            command="$outpost setup -v $projectdir",
            pool="console",
        )

        self._ninja.rule(
            "outpost_relocation",
            description="outpost project relocation",
            command="$outpost relocate -v $projectdir",
            pool="console",
        )

    def add_outpost_targets(self, project: "Project") -> None:
        self._ninja.build(
            f"build.ninja",
            "outpost_reconfigure",
            variables={"projectdir": project.topdir},
            implicit=os.path.join(project.topdir, "project.toml"),
        )

        # XXX:
        # may depends on actually installed elf instead of install target
        # may declare output correctly too.
        # This apply to all meson targets too
        self._ninja.build(
            "relocate",
            "outpost_relocation",
            variables={"projectdir": project.topdir},
            implicit=[f"{package.name}_install" for package in project._packages],
        )

    def add_meson_rules(self) -> None:
        self._ninja.newline()
        self._ninja.rule(
            "meson_setup",
            description="meson setup $name",
            command="$mesonbuild setup --cross-file=$crossfile $opts $builddir $sourcedir",
            pool="console",
        )

        self._ninja.rule(
            "meson_compile",
            description="meson compile $name",
            pool="console",
            command="$mesonbuild compile -C $builddir",
        )

        self._ninja.rule(
            "meson_install",
            description="meson install $name",
            pool="console",
            command="$mesonbuild install --only-changed --destdir $stagingdir -C $builddir",
        )

        self._ninja.newline()

    def add_meson_package(self, package: "Package") -> None:
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
        self._ninja.build(f"{package.name}_setup", "phony", f"{package.builddir}/build.ninja")
        self._ninja.build(
            f"{package.name}_compile",
            "meson_compile",
            implicit=f"{package.name}_setup",
            variables={
                "builddir": package.builddir,
                "name": package.name,
            },
        )
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
