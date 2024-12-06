# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, BaseLoader

from .package import Package
from ..utils.environment import ExeWrapper


class LocalRegistry:
    def __init__(self, path: Path) -> None:
        self._path = path
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
            self._cargo.index(subcmd=["init"], dl=self._path.as_uri(), index=str(self.index))

    def add(self, *, manifest: Path, no_verify: bool = True) -> None:
        """Add a new package to registry index."""
        self._cargo.index(
            subcmd=["add"],
            manifest_path=str(manifest.resolve(strict=True)),
            index=str(self.index),
            index_url=self.path.as_uri(),
            upload=str(self.path),
            extra_opts={"no-verify": no_verify},
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
        return list()

    @property
    @lru_cache
    def manifest(self) -> Path:
        return (self.src_dir / "Cargo.toml").resolve(strict=True)

    def deploy_local(self, registry: LocalRegistry, config: Config) -> None:
        registry.add(manifest=self.manifest)
        # TODO: fetch version from cargo manifest
        config.patch_crate_registry(name=self.name, version=self._scm.revision)

    def post_download_hook(self): ...

    def post_update_hook(self): ...
