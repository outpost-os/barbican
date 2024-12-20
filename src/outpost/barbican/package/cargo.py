# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import json
import shutil

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, BaseLoader

from .package import Package
from ..utils.environment import ExeWrapper, find_program


class Metadata:
    def __init__(self, manifest_path: Path) -> None:
        self._cargo = ExeWrapper("cargo", capture_out=True)
        self._metadata = json.loads(
            self._cargo.metadata(
                manifest_path=str(manifest_path.resolve(strict=True)),
                no_deps=True,
                quiet=True,
                format_version=1,
            )
        )

    def package_version(self, name: str) -> str | None:
        p = list(filter(lambda x: x["name"] == name, self._metadata["packages"]))
        return None if len(p) != 1 else p[0]["version"]


class LocalRegistry:
    def __init__(self, path: Path) -> None:
        self._path = path
        # Check for cargo extension cargo-index (but wrapp call as cargo subcommand)
        find_program("cargo-index")
        self._cargo = ExeWrapper("cargo")

    @property
    @lru_cache
    def name(self) -> str:
        return self._path.name

    @property
    @lru_cache
    def path(self) -> Path:
        return self._path

    @property
    @lru_cache
    def index(self) -> Path:
        return self._path / "index"

    @property
    @lru_cache
    def exists(self) -> bool:
        return (self.index / ".cargo-index-lock").exists()

    def init(self) -> None:
        """Initialize a new cargo registry index."""
        if not self.exists:
            if self.index.exists():
                shutil.rmtree(self.index)
            self._cargo.index(subcmd=["init"], dl=self._path.as_uri(), index=str(self.index))

    def publish(self, *, name: str, version: str, manifest: Path, target_dir: Path) -> None:
        """Package a new cate and push to local registry index."""
        crate_filename = f"{name}-{version}.crate"
        crate_index_filepath = self.index / name[:2] / name[2:4] / name
        if crate_index_filepath.exists():
            crate_index_filepath.unlink()
        self._cargo.package(
            manifest_path=str(manifest),
            target_dir=str(target_dir),
            no_verify=True,
            allow_dirty=True,
        )
        self._cargo.index(
            subcmd=["add"],
            crate=str(target_dir / "package" / crate_filename),
            index=str(self.index),
            index_url=self.path.as_uri(),
            upload=str(self.path),
            force=True,
        )


class Config:

    template: str = """
[registries.{{ registry.name }}]
index = "{{ registry.index.as_uri() }}"

[source.{{ registry.name }}]
registry = "{{ registry.index.as_uri() }}"
replace-with = 'local-registry'

[source.local-registry]
local-registry = "{{ registry.path }}"

[net]
git-fetch-with-cli = true

{% if crates|length != 0 %}
[patch.crates-io]
{%- for name, version in crates.items() %}
{{ name }} = { version="{{ version }}", registry="{{ registry.name }}" }
{%- endfor %}
{% endif %}
"""

    def __init__(self, builddir: Path, registry: LocalRegistry) -> None:
        self._base_path = builddir
        self._local_registry = registry
        self._crates: dict[str, str] = dict()
        self.config_dir.mkdir(exist_ok=True)
        self._update()

    @property
    @lru_cache
    def config_dir(self) -> Path:
        return self._base_path / ".cargo"

    @property
    @lru_cache
    def config_filename(self) -> Path:
        return self.config_dir / "config.toml"

    def _update(self) -> None:
        template = Environment(loader=BaseLoader()).from_string(self.template)
        with self.config_filename.open(mode="w", encoding="utf-8") as config:
            config.write(template.render(registry=self._local_registry, crates=self._crates))

    def patch_crate_registry(self, name: str, version: str) -> None:
        self._crates[name] = version
        self._update()


class Cargo(Package):
    def __init__(self, name: str, parent_project, config_node: dict, type):
        super().__init__(name, parent_project, config_node, type)

    @property
    def build_options(self) -> list[str]:
        opts = list()
        opts.append("-Clto=true")
        # XXX:
        #  todo: use pic/no-pic generic opt from project.toml
        #  Hardcode no-pic (i.e. partial link, relocated and relink at build time)
        opts.append("-Clink-args=-r")
        opts.append("-Clink-args=-Wl,-entry=_start")
        return opts

    @property
    @lru_cache
    def manifest(self) -> Path:
        return (self.src_dir / "Cargo.toml").resolve(strict=True)

    def deploy_local(self, registry: LocalRegistry, config: Config) -> None:
        # TODO: fetch version from cargo manifest
        pass
        # registry.add(manifest=self.manifest)
        # config.patch_crate_registry(name=self.name, version=self._scm.revision)

    def post_download_hook(self): ...

    def post_update_hook(self): ...
