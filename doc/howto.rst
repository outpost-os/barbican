HowTo
=====

Sample project build
--------------------

Environment setup
^^^^^^^^^^^^^^^^^

Python environment
""""""""""""""""""
Barbican supports python 3.10+ and can be install from PyPI or github repository.
For use as Integration Kit, `tools` extra dependencies must be installed.

.. code-block:: console

    pip install [--user] outpost-barbican[tools]

.. seealso::

    :ref:`Getting Barbican <getting-barbican>` Section.

C environment
"""""""""""""

A GCC compiler is required w/ at least C11 support and `binutils` 2.39 as the linker needs
to support `--package-metadata option <https://systemd.io/ELF_PACKAGE_METADATA/>`_.
Pre built C toolchain for arm Cortex-M cores can be found
`here <https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads>`_.

.. tip::

    ARM developer toolchain version 12+ are mandatory, prior to 12.x, the `binutils`
    packaged version does not meet requirements.


.. todo::

    Barbican will provide C toolchain in SDK in next major releases


Rust environment
""""""""""""""""

One may use `rustup <https://www.rust-lang.org/tools/install>`_ for rust environment setup.
The following targets are supported and might be installed:
 - thumbv7em-none-eabi
 - thumbv8m.main-none-eabi

The minimum required version is 1.82
