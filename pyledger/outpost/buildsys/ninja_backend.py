# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: LicenseRef-LEDGER

import ninja_syntax  # type: ignore

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyledger.outpost.package import Package


class NinjaGenFile:
    def __init__(self, filename):
        self._raw_file = open(filename, "w")
        self._ninja = ninja_syntax.Writer(self._raw_file)

    def close(self) -> None:
        """Close, and thus write to disk, ninja build file"""
        self._raw_file.close()

    def add_meson_rules(self) -> None:
        self._ninja.variable("ninjabuild", "ninja")
        self._ninja.variable("mesonbuild", "meson")
        self._ninja.variable("crossfile", "arm-none-eabi-gcc.ini")
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
