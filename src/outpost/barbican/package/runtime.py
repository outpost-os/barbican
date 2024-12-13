# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from .package import Package
from .meson import Meson
from .cargo import LocalRegistry, Metadata, Config

from ..console import console
from ..logger import logger
from ..utils import working_directory


class Runtime:
    def __init__(self, parent, config: dict) -> None:
        self._package = Meson("runtime", parent, config["runtime"], Package.Type.Runtime)
        self._cargo_manifests = {
            "outpost_metadata": self._package.src_dir
            / "subprojects"
            / "package-metadata"
            / "Cargo.toml",
            "shield-macros": self._package.src_dir / "rust" / "macros" / "Cargo.toml",
            "shield": self._package.src_dir / "rust" / "Cargo.toml",
        }

    def install_crates(self, registry: LocalRegistry, cargo_config: Config) -> None:
        self._package.build_dir.mkdir(exist_ok=True)
        with working_directory(self._package.build_dir):
            for name, manifest in self._cargo_manifests.items():
                console.message(f"Install [b]{name}[/b] ([i]{str(manifest)}[/i]) to local registry")
                metadata = Metadata(manifest)
                version = metadata.package_version(name)
                if not version:
                    logger.warning(f"{name} version not found, skip")
                    continue
                registry.publish(
                    name=name,
                    version=version,
                    manifest=manifest,
                    target_dir=self._package.build_dir,
                )
                cargo_config.patch_crate_registry(name=name, version=version)
