# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import ninja_syntax  # type: ignore

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..utils.environment import find_program

if TYPE_CHECKING:
    from ..package import Package
    from ..barbican import Project


class NinjaGenFile:
    def __init__(self, filename):
        self._raw_file = open(filename, "w")
        self._ninja = ninja_syntax.Writer(self._raw_file, width=1024)
        self._ninja.comment("Barican build.ninja")
        self._ninja.comment("Auto generated file **DO NOT EDIT**")

    def close(self) -> None:
        """Close, and thus write to disk, ninja build file."""
        self._raw_file.close()

    def add_barbican_rules(self) -> None:
        self._ninja.newline()
        self._ninja.comment("barbican executable")
        self._ninja.variable("barbican", find_program("barbican"))
        self._ninja.newline()
        self._ninja.comment("barbican reconfiguration rule")
        self._ninja.rule(
            "barbican_reconfigure",
            description="barbican project reconfiguration",
            generator=True,
            command="$barbican setup $projectdir",
            pool="console",
        )

    def add_barbican_internals_rules(self) -> None:
        def _add_barbican_internal_rule(name: str, args: str) -> None:
            self._ninja.newline()
            self._ninja.rule(
                f"{name}",
                description=f"barbican internal {name} command",
                command=f"$barbican --internal {name} {args}",
                pool="console",
            )

        internal_commands = {
            "capture_out": "$out $cmdline",
            "gen_ldscript": "--name=$name $template $in $out",
            "gen_memory_layout": "--prefix=$prefix $out $projectdir",
            "gen_task_metadata_bin": "$out $in $projectdir",
            "kernel_fixup": "$out $in",
            "meson_package_dyndep": "--name=$name -j $json $builddir $stagingdir $out",
            "objcopy": "$out $in --format=$format $extra_option",
            "relink_elf": "$out $in --linkerscript=$lnk $options",
            "srec_cat": "--format=$format $out $in",
        }

        # XXX: to remove
        for command, args in internal_commands.items():
            _add_barbican_internal_rule(command, args)

        self._ninja.newline()
        self._ninja.rule(
            "internal",
            description="barbican internal command",
            command="$barbican --internal $cmd $args",
            pool="console",
        )

    def add_barbican_targets(self, project: "Project") -> None:
        self._ninja.newline()
        project_implicit_deps = [
            str(project.path.config_full_path),
            str(project.path.save_full_path),
        ]
        self._ninja.build(project_implicit_deps, "phony")
        self._ninja.build(
            "build.ninja",
            "barbican_reconfigure",
            variables={"projectdir": project.path.project_dir},
            implicit=project_implicit_deps,
        )

    def add_barbican_dts(self, dts: Path, dts_include_dirs: list[Path]) -> None:
        self._ninja.newline()
        self._ninja.variable("dts", str(dts.resolve(strict=True)))
        self._ninja.variable("dtsincdir", ",".join([str(d.resolve()) for d in dts_include_dirs]))

    def add_barbican_cross_file(self, crossfile: Path) -> None:
        self._ninja.newline()
        self._ninja.variable("crossfile", str(crossfile))

    def add_internal_gen_memory_layout_target(
        self,
        output: Path,
        dts: Path,
        dependencies: list,
        sys_exelist: list,
        app_exelist: list,
    ) -> list:
        self._ninja.newline()
        exelist_opt = " ".join(f" -l {str(exe.resolve())}" for exe in sys_exelist + app_exelist)
        implicit = [f"{package.name}_install.stamp" for package in dependencies]
        implicit.extend([str(exe.resolve()) for exe in app_exelist])
        return self._ninja.build(
            str(output),
            "internal",
            implicit=implicit,
            variables={
                "cmd": "gen_memory_layout",
                "args": f"{str(output)} --dts {str(dts)} {exelist_opt}",
                "description": "generating firmware memory layout",
            },
        )

    def add_internal_gen_dummy_memory_layout_target(self, output: Path) -> list:
        self._ninja.newline()
        return self._ninja.build(
            str(output),
            "internal",
            variables={
                "cmd": "gen_memory_layout",
                "args": f"--dummy {output.resolve()}",
                "description": "generating dummy memory layout",
            },
        )

    def add_gen_ldscript_target(
        self,
        name: str,
        output: Path,
        template: Path,
        layout: Path,
        package_name: Optional[str] = None,
    ) -> None:
        implicit_inputs = ["runtime_install.stamp"]
        if name != "dummy":
            implicit_inputs.append(f"{package_name if package_name else name}_install.stamp")
        self._ninja.newline()

        self._ninja.build(
            outputs=str(output.resolve()),
            rule="internal",
            inputs=str(layout.resolve()),
            implicit=implicit_inputs,
            variables={
                "cmd": "gen_ldscript",
                "args": f"--name {name} {str(template)} {str(layout)} {str(output)}",
                "description": f"generating {name} linker script",
            },
        )

    def add_relink_target(
        self,
        name: str,
        orig_elf: Path,
        output: Path,
        linkerscript: Path,
        package_name: Optional[str] = None,
    ) -> None:
        elf_in = str(orig_elf.resolve())
        elf_out = str(output.resolve())
        lnk = str(linkerscript.resolve())
        # XXX build dir !!!
        introspect = f"{package_name if package_name else name}_introspect.json"
        self._ninja.newline()
        self._ninja.build(
            rule="internal",
            outputs=elf_out,
            inputs=[lnk, introspect],
            implicit=f"{name}_install.stamp",
            variables={
                "cmd": "relink_elf",
                "args": f"-l {lnk} -m {introspect} {elf_out} {elf_in}",
                "description": f"{name}: linking {elf_out}",
            },
        )

    def add_objcopy_rule(
        self, input: Path, output: Path, format: str, deps: list[str], package_name: str
    ) -> None:
        self._ninja.newline()
        introspect = f"{package_name}_introspect.json"
        implicit_deps = [introspect]
        if deps:
            implicit_deps.extend(deps)
        self._ninja.build(
            rule="internal",
            outputs=str(output),
            inputs=[str(input)],
            implicit=implicit_deps,
            variables={
                "cmd": "objcopy",
                "args": f"-f {format} -m {introspect} {str(output)} {str(input)}",
                "description": f"objcopy {str(input)} to {str(output)}",
            },
        )

    def add_gen_metadata_rule(self, input: Path, output: Path, projectdir: Path) -> None:
        self._ninja.newline()
        self._ninja.build(
            rule="internal",
            outputs=str(output),
            inputs=[str(input)],
            variables={
                "cmd": "gen_task_metadata_bin",
                "args": f"{str(output)} {str(input)} {str(projectdir)}",
                "description": f"generate task {input.stem} metadata",
            },
        )

    def add_srec_cat_rule(self, kernel: Path, idle: Path, apps: list[Path], output: Path) -> None:
        deps = [str(kernel)]
        deps.extend([str(app) for app in apps])
        self._ninja.newline()
        self._ninja.build(
            rule="internal",
            outputs=str(output),
            inputs=deps,
            variables={
                "cmd": "srec_cat",
                "args": f"--format ihex {str(output)} " + " ".join(deps) + f" {str(idle)}",
                "description": f"generating {str(output)} with srec_cat",
            },
        )

    def add_fixup_kernel_rule(self, input: Path, output: Path, metadata: list[Path]) -> None:
        metadata_str = [str(datum) for datum in metadata]
        self._ninja.newline()
        self._ninja.build(
            rule="internal",
            outputs=str(output),
            inputs=metadata_str,
            variables={
                "cmd": "kernel_fixup",
                "args": f"{str(output)} {str(input)} {' '.join(metadata_str)}",
                "description": "kernel task metadata fixup",
            },
        )

    def add_meson_rules(self) -> None:
        self._ninja.newline()
        self._ninja.variable("mesonbuild", find_program("meson"))
        self._ninja.newline()
        self._ninja.rule(
            "meson_setup",
            description="meson setup $name",
            command="$mesonbuild setup -Ddts=$dts -Ddts-include-dirs=$dtsincdir "
            "--cross-file=$crossfile $opts $builddir $sourcedir",
            pool="console",
        )
        self._ninja.newline()
        self._ninja.rule(
            "meson_compile",
            description="meson compile $name",
            pool="console",
            command="$mesonbuild compile -C $builddir && touch $out",
        )
        self._ninja.newline()
        self._ninja.rule(
            "meson_install",
            description="meson install $name",
            pool="console",
            command="$mesonbuild install --only-changed --destdir $stagingdir -C $builddir &&"
            "touch $out",
        )

    def add_cargo_rules(self, rustargs: Path, rust_target: Path) -> None:
        self._ninja.newline()
        self._ninja.variable("cargo", find_program("cargo"))
        self._ninja.variable("rustargs", str(rustargs.resolve()))
        self._ninja.variable("rust_target", str(rust_target.resolve()))
        self._ninja.newline()
        self._ninja.rule(
            "cargo_compile",
            description="cargo compile $name",
            pool="console",
            command="cd $builddir "
            + " && config=$config $cargo build --manifest-path=$sourcedir/Cargo.toml --release"
            + " && touch $out && cd -",
        )
        self._ninja.newline()
        self._ninja.rule(
            "cargo_install",
            description="cargo install $name",
            pool="console",
            command="touch $out",
        )

    def add_cargo_package(self, package: "Package") -> None:
        self._ninja.newline()
        self._ninja.build(
            f"{package.build_dir}/.cargo/config.toml",
            "internal",
            variables={
                "cmd": "cargo_config",
                "args": f"--rustargs-file={str(package._parent._kernel.rustargs)} "
                + f"--target-file={str(package._parent._kernel.rust_target)} "
                + '--extra-args="'
                + " ".join(package.build_options)
                + '" '
                + f"{str(package.build_dir)}",
                "description": f"cargo config {package.name}",
            },
            order_only=[f"{dep}_install.stamp" for dep in package.deps],
        )
        self._ninja.newline()
        self._ninja.build(
            f"{package.name}_setup", "phony", f"{package.build_dir}/.cargo/config.toml"
        )
        self._ninja.newline()
        self._ninja.build(
            f"{package.name}_compile.stamp",
            "cargo_compile",
            variables={
                "sourcedir": package.src_dir,
                "builddir": package.build_dir,
                "name": package.name,
                "config": package._dotconfig,
            },
            implicit=f"{package.name}_setup",
        )
        self._ninja.newline()
        self._ninja.build(f"{package.name}_compile", "phony", f"{package.name}_compile.stamp")
        self._ninja.newline()

        # XXX:
        #  Cargo binary are built w/o .elf extension that is required here
        #  so split provides name and pass extension as suffix for install rule

        self._ninja.build(
            f"{package.name}_install.stamp",
            "internal",
            implicit=f"{package.name}_compile",
            variables={
                "cmd": "cargo_install",
                "args": "--suffix=.elf "
                + f"--target-file={str(package._parent._kernel.rust_target)} "
                + f"{str(package.build_dir)} "
                + " ".join((str(t.with_suffix("")) for t in package.installed_targets)),
                "description": f"cargo install {package.name}",
            },
        )

        self._ninja.newline()
        self._ninja.build(f"{package.name}_install", "phony", f"{package.name}_install.stamp")
        self._ninja.newline()

    def add_meson_package(self, package: "Package") -> None:
        self._ninja.newline()
        self._ninja.build(
            f"{package.build_dir}/build.ninja",
            "meson_setup",
            variables={
                "builddir": package.build_dir,
                "sourcedir": package.src_dir,
                "name": package.name,
                "opts": package.build_options,
            },
            order_only=[f"{dep}_install.stamp" for dep in package.deps],
        )
        self._ninja.newline()
        self._ninja.build(f"{package.name}_setup", "phony", f"{package.build_dir}/build.ninja")
        self._ninja.newline()
        self._ninja.build(
            f"{package.name}.dyndep",
            "meson_package_dyndep",
            order_only=f"{package.name}_setup",
            variables={
                "name": package.name,
                "builddir": package.build_dir,
                "stagingdir": package.staging_dir,
                "json": f"{package.name}_introspect.json",
            },
            implicit_outputs=f"{package.name}_introspect.json",
        )

        self._ninja.newline()
        self._ninja.build(
            f"{package.name}_compile.stamp",
            "meson_compile",
            variables={
                "builddir": package.build_dir,
                "name": package.name,
                "dyndep": f"{package.name}.dyndep",
            },
            order_only=f"{package.name}.dyndep",
        )
        self._ninja.newline()
        self._ninja.build(f"{package.name}_compile", "phony", f"{package.name}_compile.stamp")
        self._ninja.newline()
        self._ninja.build(
            f"{package.name}_install.stamp",
            "meson_install",
            variables={
                "builddir": package.build_dir,
                "name": package.name,
                "stagingdir": package.staging_dir,
                "dyndep": f"{package.name}.dyndep",
            },
            order_only=f"{package.name}.dyndep",
        )

        self._ninja.newline()
        self._ninja.build(f"{package.name}_install", "phony", f"{package.name}_install.stamp")
        self._ninja.newline()
