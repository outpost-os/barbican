# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
import json
from pathlib import Path
import subprocess
import typing as T

from ..utils.environment import find_program


# XXX: Add an helper module in utils
def _meson_package_get_objcopy(introspect: Path) -> str:
    with introspect.open("r") as file:
        introspect_json = json.load(file)
        compiler = Path(introspect_json["compilers"]["host"]["c"]["exelist"][0])
        toolchain_path = compiler.parent
        triple, _ = compiler.name.rsplit("-", 1)
        return find_program(triple + "-objcopy", toolchain_path)


def run_objcopy(objcopy: str, input: Path, output: Path, bfdname: str) -> None:
    cmdline: list[str] = [objcopy]
    cmdline.extend(
        ["-O", bfdname, "--remove-section=.note*", str(input.resolve()), str(output.resolve())]
    )
    subprocess.run(cmdline, check=True)


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("output", type=Path, help="output file")
    parser.add_argument("input", type=Path, help="input elf file")
    parser.add_argument(
        "-f", "--format", type=str, choices=["ihex"], required=True, help="output format"
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

    objcopy = None
    if args.mesonintrospect:
        objcopy = _meson_package_get_objcopy(args.mesonintrospect)

    if not objcopy:
        raise Exception("please specify the objcopy to use")

    run_objcopy(objcopy, args.input, args.output, args.format)
