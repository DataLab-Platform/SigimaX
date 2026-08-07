# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.
"""
Adapters for PlotPy
===================

The :mod:`sigimax.adapters_plotpy` package provides adapters for
PlotPy to integrate with SigimaX's data model and GUI.

Each Sigima object (:class:`~sigima.objects.SignalObj`,
:class:`~sigima.objects.ImageObj`, ROI classes) is converted to/from PlotPy
plot items by a dedicated adapter class. :class:`PlotPyAdapterFactory`
resolves which adapter class to use for a given object; derived applications
subclass the factory to override or extend this resolution and install it
with :func:`set_adapter_factory`.

.. autoclass:: PlotPyAdapterFactory
    :members:
.. autofunction:: get_adapter_factory
.. autofunction:: set_adapter_factory
.. autofunction:: reset_adapter_factory
.. autofunction:: create_adapter_from_object
.. autoclass:: SignalObjPlotPyAdapter
    :members:
.. autoclass:: ImageObjPlotPyAdapter
    :members:
.. autoclass:: SegmentROIPlotPyAdapter
    :members:
.. autoclass:: SignalROIPlotPyAdapter
    :members:
.. autoclass:: RectangularROIPlotPyAdapter
    :members:
.. autoclass:: CircularROIPlotPyAdapter
    :members:
.. autoclass:: PolygonalROIPlotPyAdapter
    :members:
.. autofunction:: items_to_json
.. autofunction:: json_to_items
.. autofunction:: plotitem_to_singleroi
.. autofunction:: singleroi_to_plotitem
.. autofunction:: configure_roi_item
"""

from __future__ import annotations

from .base import items_to_json, json_to_items
from .converters import (
    create_adapter_from_object,
    plotitem_to_singleroi,
    singleroi_to_plotitem,
)
from .factories import (
    PlotPyAdapterFactory,
    get_adapter_factory,
    reset_adapter_factory,
    set_adapter_factory,
)
from .objects.base import TypePlotItem
from .objects.image import (
    ImageObjPlotPyAdapter,
)
from .objects.signal import CURVESTYLES, SignalObjPlotPyAdapter
from .roi.base import TypeROIItem, configure_roi_item
from .roi.image import (
    CircularROIPlotPyAdapter,
    PolygonalROIPlotPyAdapter,
    RectangularROIPlotPyAdapter,
)
from .roi.signal import SegmentROIPlotPyAdapter, SignalROIPlotPyAdapter

__all__ = [
    "CURVESTYLES",
    "CircularROIPlotPyAdapter",
    "ImageObjPlotPyAdapter",
    "PlotPyAdapterFactory",
    "PolygonalROIPlotPyAdapter",
    "RectangularROIPlotPyAdapter",
    "SegmentROIPlotPyAdapter",
    "SignalObjPlotPyAdapter",
    "SignalROIPlotPyAdapter",
    "TypePlotItem",
    "TypeROIItem",
    "configure_roi_item",
    "create_adapter_from_object",
    "get_adapter_factory",
    "items_to_json",
    "json_to_items",
    "plotitem_to_singleroi",
    "reset_adapter_factory",
    "set_adapter_factory",
    "singleroi_to_plotitem",
]
