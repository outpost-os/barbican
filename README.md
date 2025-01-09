<!--
SPDX-FileCopyrightText: 2024 - 2025 Ledger SAS

SPDX-License-Identifier: Apache-2.0
-->

# Outpost Barbican

Barbican is the Outpost OS meta tools for building project, SDK and integration,
written in python.

## Dependencies
 - Python >= 3.10
 - Jinja2 >= 3.1.0
 - jinja-cli >= 1.2.0
 - jsonschema >= 4.18.0
 - kconfiglib >= 14.1.0
 - lief >= 0.13,<0.15
 - meson >= 1.4.0,<1.5.0
 - ninja >= 1.11.0
 - ninja_syntax > 1.7
 - svd2json >= 0.1.6
 - dts-utils >= 0.3.0
 - tomli >= 2.0.1; python_version < '3.11'
 - referencing >= 0.33.0
 - rich >= 13.6
 - GitPython >= 3.1.43

## Usage

A project is describe by a toml configuration file, a dts for the targeted SoC
and `Kconfig` `dotconfig` for kernel and application(s).

### Configuration

The following is the sample project configuration describing a simple project with
simple application(s)

```toml
name = 'HelloWorld Project'
license = 'Apache-2.0'
license_file = ['LICENSE.txt']
dts = 'dts/sample.dts'
crossfile = 'cm33-none-eabi-gcc.ini'
version = 'v0.0.1'

[kernel]
scm.git.uri = 'https://github.com/outpost-os/sentry-kernel.git'
scm.git.revision = 'main'
config = 'configs/sentry/nucleo_u5a5.config'

[runtime]
scm.git.uri = 'git@github.com:outpost-os/shield.git'
scm.git.revision = 'main'
config = 'configs/shield/shield.config'

[application.hello]
scm.git.uri = 'https://github.com/outpost-os/sample-rust-app.git'
scm.git.revision = 'main'
config = 'configs/hello/hello.config'
build.backend = 'cargo'
depends = []
provides = ['hello.elf']
```

### Download

Downloads kernel/runtime and applications describe in `project.toml` to src directory

```console
barbican download
```
### Update

Updates sources if configuration change and/or revision update.
Package need to be already downloaded to be updated.

```console
barbican update
```
### Setup

Generates jinja build script for project build (i.e. kernel, runtime, application and
firmware integration). Files are generated in build directory.

```console
barbican setup
```

### Build

```console
cd output/build
ninja
```

## TODO

 - SDK generation
 - Pre built C and Rust toolchain in SDK

## License

```
Copyright 2024 - 2025 Ledger SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
