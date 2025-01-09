HowTo
=====

Environment setup
-----------------

Python environment
^^^^^^^^^^^^^^^^^^
Barbican supports python 3.10+ and can be install from PyPI or github repository.
For use as Integration Kit, `tools` extra dependencies must be installed.

.. code-block:: console

    pip install [--user] outpost-barbican[tools]

.. seealso::

    :ref:`Getting Barbican <getting-barbican>` Section.

C environment
^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^

One may use `rustup <https://www.rust-lang.org/tools/install>`_ for rust environment setup.
The following targets are supported and might be installed:
 - thumbv7em-none-eabi
 - thumbv8m.main-none-eabi

The minimum required version is 1.82

Sample applications
-------------------

Outpost application must be linked with shield runtime and a minimal Kconfig based configuration
is required for package metadata generation. Meson (C lang) and Cargo (Rust lang) are
the supported buildsystem for application. The following will describe the minimal build
recipe for a HelloWorld application.

.. todo::

    Add examples w/ SDK once available

.. note::

    Project integration scenario only

Meson/C application
^^^^^^^^^^^^^^^^^^^

Meson is the preferred buidsystem for C based application.

Internal dependencies
=====================

Internal dependencies are handled using `Meson wrap file <https://mesonbuild.com/Wrap-dependency-system-manual.html>`_.
Those dependencies are set of meson recipe providing integration helper.

 - `Outpost devicetree <https://github.com/outpost-os/outpost-devicetree.git>`_
    Provides devicetree preprocessing and tool for code generation base on dts.
 - `Outpost kconfig <https://github.com/outpost-os/outpost-kconfig.git>`_
    Provides kconfig parsing and C header generation based on `.config` and `Kconfig` files.
 - `Outpost package metadata <https://github.com/outpost-os/outpost-package-metadata.git>`_
    Generates package metadata based on kernel/runtime dependencies and task configuration.

.. note::

    Shield runtime is part of SDK/staging and thus not an internal dependency.

Required Meson Options
======================

Barbican integration requires the following Meson options to be defined:

 - config: Configuration (`.config`) file to use
 - dts: Top level device tree source (`dts`)
 - dts-include-dirs: extra path for device tree source fragment (`dtsi`) look up.

.. code-block:: python
    :caption: meson.options
    :name: sample_meson_options
    :linenos:

    option('config', type: 'string', description: 'Configuration file to use', yield: true)
    option('dts', type: 'string', description: 'Top level DTS file', yield: true)
    option('dts-include-dirs', type: 'array', yield: true,
       description: 'Directories to add to resolution path for dtsi inclusion')


Kconfig
=======

At least, the application must included the outpost task Kconfig file for task configuration

.. todo::

    Add cross ref to Sentry UAPI kconfig documentation

.. code-block::
    :caption: Kconfig
    :name: sample_kconfig
    :linenos:

    mainmenu "Sample C app"

    menu "task properties"
    osource "$(sdk)/share/configs/task.Kconfig"
    endmenu

    endif

Meson Recipe
============

.. code-block:: meson
    :caption: meson.build
    :name: sample_meson_build
    :linenos:

    project('sample-c-app', 'c')

    # internal dep for kconfig handling
    kconfig_file = meson.current_source_dir() / 'Kconfig'
    kconfig_proj = subproject('kconfig', default_options: ['kconfig=@0@'.format(kconfig_file)])
    kconfig_h = kconfig_proj.get_variable('kconfig_h')
    kconfig_data = kconfig_proj.get_variable('kconfig_data')

    # internal dep for package metadata generation and link
    elf_pkg_metadata_proj = subproject('elf-package-metadata')
    elf_pkg_metadata_dep = elf_pkg_metadata_proj.get_variable('package_metadata_dep')
    external_deps = [ elf_pkg_metadata_dep ]

    # runtime external dep from SDK or staging dir
    libshield_dep = dependency('shield')
    external_deps += [ libshield_dep ]

    sample_app_elf = executable(
        meson.project_name(),
        name_suffix: 'elf',
        sources: [ 'src/main.c' ],
        include_directories: [ 'include' ],
        dependencies: [ external_deps ],
        link_language: 'c',
        install: true,
    )


.. code-block:: C
    :caption: main.c
    :name: sample_app_main
    :linenos:

    #include <stdio.h>

    int main(void)
    {
        printf("Hello World Outpost\n");
        return 0;
    }

.. seealso::

    `C sample application repository <TODO>`_

Cargo/Rust application
^^^^^^^^^^^^^^^^^^^^^^

Cargo is the preferred buildsystem for Rust based application.

Internal dependencies
=====================

A local registry is located in the SDK/staging with all internal dependencies and runtime.
At project output top level, a cargo config file overrides dependencies in order to use
SDK provided ones.

Cargo Recipe
============

.. code-block:: toml
    :caption: Cargo.toml
    :name: sample_cargo_toml
    :linenos:

    [package]
    name = "hello"
    version = "0.1.0"
    edition = "2021"

    [profile.release]
    lto = true
    opt-level = "s"

    [dependencies]
    shield = "0.1"

    [build-dependencies]
    outpost_metadata =  "0.1"


.. code-block:: rust
    :caption: build.rs
    :name: sample_build_rs
    :linenos:

    use std::env;

    fn main() {
        // Generates cargo introspection metadata
        let metadata =
            outpost_metadata::cargo_package_introspect(env::var("CARGO_MANIFEST_PATH").ok().as_deref());
        // Generates package metadata using cargo metadata and .config file.
        // configuration file is pass to build script using `config` environment variable
        // see: `Outpost kconfig <https://github.com/outpost-os/outpost-kconfig>`_ rust documentation
        let _ = outpost_metadata::gen_package_metadata(
            env::var("CARGO_PKG_NAME").unwrap().as_str(),
            metadata,
            env::var("config").ok().as_deref(),
            None,
        );
    }

.. code-block:: rust
    :caption: main.rs
    :name: sample_main_rs
    :linenos:

    #![cfg_attr(target_os = "none", no_std)]
    #![cfg_attr(target_os = "none", no_main)]

    extern crate shield;
    use shield::println;

    #[cfg(target_os = "none")]
    shield::shield_main!();

    fn main() {
        println!("Hello, World !");
    }

.. seealso::

    `Cargo/Rust sample application repository <https://github.com/outpost-os/sample-rust-app.git>`_

Sample project
--------------
