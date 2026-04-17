.. _installation:

Installation
============

This section provides instructions on how to install and set up SigimaX,
including dependencies and environment configuration.

How to install
--------------

SigimaX is available in several forms:

-   As a Python package, which can be installed using the :ref:`install_pip`.

-   As a precompiled :ref:`install_wheel`, which can be installed using ``pip``.

-   As a :ref:`install_source`, which can be installed from the Git repository.

.. seealso::

    Impatient to try the next version of SigimaX? You can also install the
    latest development version from the main branch of the Git repository.
    See :ref:`install_development` for more information.

.. _install_pip:

Package manager ``pip``
^^^^^^^^^^^^^^^^^^^^^^^

:octicon:`info;1em;sd-text-info` :bdg-info-line:`GNU/Linux` :bdg-info-line:`Windows` :bdg-info-line:`macOS`

SigimaX's package ``sigimax`` is available on the Python Package Index (PyPI)
at: https://pypi.python.org/pypi/sigimax.

Install SigimaX by running:

.. code-block:: console

    $ pip install sigimax

.. note::

    If you already have a previous version of SigimaX installed, you can
    upgrade it by running the same command with the ``--upgrade`` option:

    .. code-block:: console

        $ pip install --upgrade sigimax

.. _install_wheel:

Wheel package
^^^^^^^^^^^^^

:octicon:`info;1em;sd-text-info` :bdg-info-line:`GNU/Linux` :bdg-info-line:`Windows` :bdg-info-line:`macOS`

On any operating system, using pip and the Wheel package is the easiest way to
install SigimaX on an existing Python distribution:

.. code-block:: console

    $ pip install --upgrade sigimax-0.1.0-py2.py3-none-any.whl

.. _install_source:

Source package
^^^^^^^^^^^^^^

:octicon:`info;1em;sd-text-info` :bdg-info-line:`GNU/Linux` :bdg-info-line:`Windows` :bdg-info-line:`macOS`

Installing SigimaX directly from the source package may be done using ``pip``:

.. code-block:: console

    $ pip install --upgrade sigimax-0.1.0.tar.gz

Or, if you prefer, you can install it in editable mode from the root directory
of the source package:

.. code-block:: console

    $ pip install -e .

.. _install_development:

Development version
^^^^^^^^^^^^^^^^^^^

:octicon:`info;1em;sd-text-info` :bdg-info-line:`GNU/Linux` :bdg-info-line:`Windows` :bdg-info-line:`macOS`

If you want to try the latest development version of SigimaX, you can install
it directly from the main branch of the Git repository.

The first time you install SigimaX from the Git repository, enter the following
command:

.. code-block:: console

    $ pip install git+https://github.com/DataLab-Platform/SigimaX.git

Then, if at some point you want to upgrade to the latest version, run:

.. code-block:: console

    $ pip install --force-reinstall --no-deps git+https://github.com/DataLab-Platform/SigimaX.git

.. note::

    If dependencies have changed, you may need to execute the same command
    without the ``--no-deps`` option.

Dependencies
------------

.. include:: ../requirements.rst
