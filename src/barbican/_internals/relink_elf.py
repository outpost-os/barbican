# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
import json
from pathlib import Path
import subprocess
import typing as T


# XXX: Add an helper module in utils
def _meson_package_get_linker(introspect: Path) -> list[str]:
    with introspect.open("r") as file:
        introspect_json = json.load(file)
        return introspect_json["compilers"]["host"]["c"]["linker_exelist"]


def run_relink_elf(
    linker_cmdline: list[str], input: Path, output: Path, linkerscript: Path
) -> None:

    linker_cmdline.extend(["-o", str(output.resolve())])
    linker_cmdline.extend(
        [
            str(input.resolve()),
            "-Wl,--as-needed",
            "-Wl,--no-undefined",
            "-nostartfiles",
            "-nodefaultlibs",
            "-Wl,--gc-sections",
            "-Wl,--cref",
            "-static",
            f"-T{str(linkerscript.resolve())}",
            f"-Wl,-Map={output.parent / output.stem}.map",
        ]
    )

    subprocess.run(linker_cmdline, check=True)


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("output", type=Path, help="output elf file")
    parser.add_argument("input", type=Path, help="partially linked input elf")
    parser.add_argument(
        "-l", "--linkerscript", type=Path, required=True, help="linker script to use"
    )
    parser.add_argument(
        "-m",
        "--mesonintrospect",
        type=Path,
        required=False,
        help="Meson introspect json (for Meson package only)",
    )

    return parser


def run(argv: T.List[str]) -> None:
    args = argument_parser().parse_args(argv)
    linker_cmdline = None
    if args.mesonintrospect:
        linker_cmdline = _meson_package_get_linker(args.mesonintrospect)

    if not linker_cmdline:
        raise Exception("please specify a linker to relink the given elf file")

    run_relink_elf(linker_cmdline, args.input, args.output, args.linkerscript)
