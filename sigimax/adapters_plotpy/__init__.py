# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.
"""
Adapters for PlotPy
===================

The :mod:`sigimax.adapters_plotpy` package provides adapters for
PlotPy to integrate with SigimaX's data model and GUI.
"""

from __future__ import annotations

from .base import items_to_json, json_to_items
from .converters import (
    create_adapter_from_object,
    plotitem_to_singleroi,
    singleroi_to_plotitem,
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
    "PolygonalROIPlotPyAdapter",
    "RectangularROIPlotPyAdapter",
    "SegmentROIPlotPyAdapter",
    "SignalObjPlotPyAdapter",
    "SignalROIPlotPyAdapter",
    "TypePlotItem",
    "TypeROIItem",
    "configure_roi_item",
    "create_adapter_from_object",
    "items_to_json",
    "json_to_items",
    "plotitem_to_singleroi",
    "singleroi_to_plotitem",
]
