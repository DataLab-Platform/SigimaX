# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX package metadata
=========================

This module centralizes package-level metadata (version, URLs) in a single
file that has **no internal imports**.

Why a separate module?
~~~~~~~~~~~~~~~~~~~~~~

SigimaX is a framework library whose ``__init__.py`` re-exports key symbols
(``SGMXMainWindow``, ``create``, ``run``) for convenience.  Those re-exports
pull in heavy submodules (``sigimax.app``, ``sigimax.mainwindow``) which
eventually import ``sigimax.config``.  If ``sigimax.config`` were to import
metadata back from ``sigimax.__init__``, a circular import chain would form::

    sigimax → sigimax.mainwindow → sigimax.widgets.* → sigimax.config → sigimax

By placing the metadata here, both ``__init__.py`` and ``config.py`` can
import it without triggering the cycle.  This is the same pattern used by
projects like Flask and setuptools-scm that need a rich ``__init__.py``
alongside internal access to version information.
"""

__version__ = "0.1.0"
__docurl__ = "https://sigimax.readthedocs.io/"
__homeurl__ = "https://github.com/DataLab-Platform/SigimaX"
__supporturl__ = "https://github.com/DataLab-Platform/SigimaX/issues/new/choose"
