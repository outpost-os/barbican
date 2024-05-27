<!--
SPDX-FileCopyrightText: 2024 Ledger SAS

SPDX-License-Identifier: Apache-2.0
-->

# Ledger python package template repository

This repository is made in order to be used as a clean
basis to produce python packages to be exported to a pypi repository.

This repository aim to comply to, at least, PEP420, PEP 517, PEP 621 and PEP 660.

The goal is to modify the content of the pyledger namespace,
adding your own package name and content, and use the overall python ecosystem
supported in this very repository to build, check and deploy your package.

## Using Docker

This package can be fully manipulated (building, testing, deploying)
with the `docker-kulos-nexus.orange.ledgerlabs.net/pythonbot` Docker image.
This can be done through the usual `docker run` or through
the `.devcontainer.json` vscode file for vscode users.

## Personalising from this template

This template deploy an empty python package using the `pyledger` python namespace,
in which a `template` custom package is created. This package hold a stub library,
and deploy a custom associated `templatebin` executable automatically (see `pyproject.toml` file).

The goal here is to update the package name and content based on your need,
keeping all the python related element (CI/CD, build system, linting and so on)
in order to reduce as much as possible to work associated to the build and quality system.

When creating an effective package repository from this template, you need to:

   1. Rename the `pyledger/template` directory with a real `pyledger` package name
      (other than template), and write a clean content in it.
      Just keep the `__version__` definition line in the `__init__.py` file as-is,
      as it is automatically updated using vcs information
   1. Replace the occurrences of `template` in `tox.ini` file with your package name
   1. Replace the occurrences of `template` in `pyproject.tom` file with your package name.
      This includes the _name_ and _description_ fields,
      the _dynamic versioning target_ file path and the _homepage_
   1. Update (or remove) the `tool.poetry.script` field depending on your needs
      (executable(s) needed or not)
   1. Replace `env.PROJECTNAME` variable in the `.github/workflows/main.yml` file
   1. Replace the `tests/test_template.py` with your `pytest` testsuite

That is all ! The build system is ready and you can use the below commands.

## Building

Build the package can be done directly using `poetry`:

```console
poetry build
```

This command performs the following steps:

* Parse the `pyproject.toml` file,
* Calculate the effective project requirements (`poetry.lock` file),
* Install the build-depends package in a python venv,
* Build the package.

The result is saved in the `dist/` subdirectory.

## Updating version

The package version is automatically managed based on semver and vcs versioning and tagging.
This is made through `poetry dynamic versioning`, as set in the `pyproject.toml` file,
in the `tools.poetry-dynamic-versioning` block.

Updating the version is made using:

```console
poetry dynamic-versioning
```

This update in the very same time both the `pyproject.toml` and the `_version.py` file version,
based on the current VCS state. The version mapping is using dirty flag and metadata (git hash) infos.
See <https://pypi.org/project/poetry-dynamic-versioning/> for more information.

## Updating dependencies

Dependencies are declared in the `pyproject.toml` file (PEP-517), including separated dependency groups
for development cases (typically unit testing, PEP-660).

When updating the dependency list, the lock file needs to be updated.
This is done using:

```console
poetry lock
```

This command performs the following steps:

* Parse the `pyproject.toml`
* Recalculate the overall dependency list
* Check potential incompatibilties
* Forge the effective dependencies for various cases (install, development, etc.).

## Running the overall testsuite

### Basics

The testsuite is fully manipulated through Tox (<https://tox.wiki/en/latest/>).
This allows to execute the overall testsuite, linter execution, coverage calculation
and reporting through a fully integrated framework.

Basic usage:

```console
tox run
```

When executing this command, tox execute all the successive steps declared in the `tox.ini` file.

This includes a linter pass, based on the tools `black`, `mypy` and `flake8`.
Then the `htmlcov` target is executed. This executes the pytest based unit test suite,
associated with `coverage` for the test coverage calculation.
The coverage report is saved as a standalone website in the `htmlcov/` directory,
giving the overall package coverage.

The Test Suite provide 3 targets that can be executed independently of each others:

* `lint`: linters execution
  * `mypy`: static typing analysis. Report is in `./mypycov` directory
  * `flake8`: PEP8 linter validator Report is in `./flakereport` directory
  * `black`: python code formatter. Returns diff between your code and the `pycodestyle` model.
* `unittests`: unit testing using `pytest`, without code coverage
* `htmlcov`: unit testing using `coverage` with code coverage. Report is in `./htmlcov` directory.

This can be done by executing the following:

```console
tox -e lint
tox -e unittests
tox -e htmlcov
```

### Using multiple python versions

If the host has multiple python versions installed, `tox` can execute its testenv
on multiple versions explicitly using the pre-defined environments.

For example, executing the tox `testenv` testsuite (corresponding to the unit-testing)
on the Python 3.10 environment can be done using:

```console
tox -e py310
```

ToX always use virtual environments, that are deployed in the `.tox` local directory,
allowing concurrent execution of multiple environments if needed.
All package dependencies are installed in the local virtualenv, without impacting the host.

Forcing ToX to recreate the environment (redeploy the virtual env) is done using the `-r` option.

## Publishing

Publishing the package can be done using poetry's `publish` target, as described in the manual.
