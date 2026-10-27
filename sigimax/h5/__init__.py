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

NeXus ``NXdata`` groups are shown as single nodes, imported as signals or images
with their axes (:mod:`sigimax.h5.nexus`); their auxiliary signals are shown as
nodes of their own. Datasets of three dimensions or more are imported through
views, one signal or image per frame (:mod:`sigimax.h5.views`), and views of
multidimensional datasets are read with
:func:`sigimax.h5.selection.read_selection`.

.. autoclass:: sigimax.h5.nexus.NXdataNode
.. autoclass:: sigimax.h5.nexus.AuxiliarySignalNode
.. autofunction:: sigimax.h5.nexus.describe_nxdata
.. autofunction:: sigimax.h5.nexus.describe_auxiliary_signals
.. autofunction:: sigimax.h5.nexus.describe_signal
.. autofunction:: sigimax.h5.nexus.default_nxdata_path
.. autofunction:: sigimax.h5.nexus.entry_information
.. autodata:: sigimax.h5.nexus.UNIFORM_AXIS_TOLERANCE

Files without suitable ``NXdata`` groups are described by declarative data
mappings (:mod:`sigimax.h5.mapping`), registered by applications or plugins.

.. autofunction:: sigimax.h5.mapping.mapping_from_dict
.. autofunction:: sigimax.h5.mapping.load_mapping
.. autofunction:: sigimax.h5.mapping.register_mapping
.. autofunction:: sigimax.h5.mapping.unregister_mapping
.. autofunction:: sigimax.h5.mapping.describe_mapping
.. autoclass:: sigimax.h5.mapping.DataMapping
.. autoclass:: sigimax.h5.mapping.MappedObject
.. autoclass:: sigimax.h5.mapping.MappedAxis
.. autoclass:: sigimax.h5.mapping.MappedDataNode
.. autoclass:: sigimax.h5.selection.NDSelection
    :members:
.. autoclass:: sigimax.h5.selection.NDView
    :members:
.. autofunction:: sigimax.h5.selection.default_view
.. autofunction:: sigimax.h5.selection.read_selection
.. autofunction:: sigimax.h5.selection.preview_step
.. autoclass:: sigimax.h5.views.NDViewMixin
    :members:
.. autoclass:: sigimax.h5.views.FrameNode
.. autofunction:: sigimax.h5.views.expand_views
.. autofunction:: sigimax.h5.utils.unavailable_filters
"""

__all__ = [
    "H5Importer",
]

# pylint: disable=unused-import

# Compression filters of detector data (bitshuffle/LZ4, Blosc, Zstandard...),
# available to h5py once registered by hdf5plugin
import hdf5plugin  # noqa: F401

# Registering dynamic I/O features:
from sigimax.h5 import generic, mapping, nexus  # noqa: F401
from sigimax.h5.common import H5Importer  # noqa: F401
