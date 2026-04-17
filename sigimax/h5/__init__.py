# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.


"""
SigimaX HDF5 I/O module (:mod:`sigimax.h5`)
============================================
"""

__all__ = [
    "H5Importer",
]

# pylint: disable=unused-import

# Registering dynamic I/O features:
from sigimax.h5 import generic  # noqa: F401
from sigimax.h5.common import H5Importer  # noqa: F401
