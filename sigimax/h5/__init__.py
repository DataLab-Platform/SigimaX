# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.


"""
SigimaX HDF5 I/O module (:mod:`sigimax.h5`)
============================================

The importer walks an HDF5 file and turns each dataset into a
:class:`~sigimax.h5.common.BaseNode` subclass instance, selected by the
module-level :data:`~sigimax.h5.common.NODE_FACTORY` registry. Applications
extend the supported data model by subclassing
:class:`~sigimax.h5.common.BaseNode` (or :class:`~sigimax.h5.common.GroupNode`)
and registering it with ``NODE_FACTORY.register(MyNode)`` — see
:doc:`../user_guide/hdf5_workspace` for a worked example.

.. autoclass:: sigimax.h5.common.H5Importer
    :members:
.. autoclass:: sigimax.h5.common.NodeFactory
    :members:
.. autoclass:: sigimax.h5.common.BaseNode
    :members:
.. autoclass:: sigimax.h5.common.GroupNode
    :members:
.. autoclass:: sigimax.h5.common.RootNode
    :members:
"""

__all__ = [
    "H5Importer",
]

# pylint: disable=unused-import

# Registering dynamic I/O features:
from sigimax.h5 import generic  # noqa: F401
from sigimax.h5.common import H5Importer  # noqa: F401
