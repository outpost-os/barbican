Getting Barbican
================

Barbican is written in Python3 and requires Python3.10 and higher. The package
is distributed though PyPI. For developers, the source code can be downloaded
from github project release page (Add ref) or from git.

Installing Barbican with pip
----------------------------

Barbican can be installed with pip, it is recommended to install package for user (or in
virtualenv).

.. code-block:: console

    pip install [--user] outpost-barbican

.. note::
    Do not install for user in a virtualenv.

.. tip::

    Barbican can be install from source as editable package for development purpose.
    From source top directory, use the following command:

    .. code-block:: console

        pip install -e .

Dependencies
------------

Build dependencies
^^^^^^^^^^^^^^^^^^

Barbican package use a `pyproject.toml` and is compliant to `PEP517/518/621`.
The build backend used is `setuptools` with dynamic versioning.

.. admonition:: depends on

     * setuptools
     * setuptools_scm

Runtime dependencies
^^^^^^^^^^^^^^^^^^^^^

Barbican depends on some packages at runtime for git operation, elf analysis and
patch, rich console rendering and so on.

.. admonition:: depends on

     * GitPython
     * kconfiglib
     * lief
     * meson
     * ninja

Extra dependencies
^^^^^^^^^^^^^^^^^^

devel
"""""

Barbican `devel` extra dependencies are the set of tools used by developers for
python linting, type checking, unit testing.

.. admonition:: depends on

     * blake
     * flake8
     * mypy
     * pytest

.. code-block:: console

    pip install [--user] outpost-barbican[devel]

doc
"""

Barbican `doc` extra dependencies are the set of tools for building the
documentation. Documentation is based on `Sphinx` and the chosen docstring style
is `numpydoc <https://numpydoc.readthedocs.io/en/latest/index.html>`_

.. admonition:: depends on

     * sphinx
     * sphinx-autoapi
     * sphinx-argparse

.. code-block:: console

    pip install [--user] outpost-barbican[doc]

tools
"""""

Barbican tools are dependencies that are used by Outpost OS package build system.
Those are not used directly by Barbican package but required in order to build
a firmware.

.. admonition:: depends on

     * Jinja2
     * svd2json
     * dts-utils

.. code-block:: console

    pip install [--user] outpost-barbican[tools]

.. tip::

    One can install all extra dependencies at once

    .. code-block:: console

        pip install [--user] outpost-barbican[devel,doc,tools]

Development
-----------

Barbican follows `PEP8 <https://peps.python.org/pep-0008/>`_ coding style, with
100 characters line length. `blake <https://black.readthedocs.io/en/stable/>`_
and `flake8 <https://flake8.pycqa.org/en/latest/>`_ are used for code linting
and type checking is done with `mypy <https://mypy-lang.org/>`_ with Python 3.10
type annotation syntax.

Barbican use `tox <https://tox.wiki/en/4.17.0/>`_ as test frontend. Lint, unit
testing and documentation generation are done in isolated build. The following
testenv are available and can be run all in once or individually.

  * lint
  * unittests
  * docs

.. code-block:: console

    tox
    tox -e lint
    tox -e unittests
    tox -e docs
