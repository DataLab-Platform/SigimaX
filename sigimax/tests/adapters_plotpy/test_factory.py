# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tier 1 — Factory and pure-unit tests (no Qt)
---------------------------------------------

Tests for :func:`create_adapter_from_object`, unsupported types,
:meth:`iterate_metadata_shape_items` default hook, and annotation roundtrip
logic that do **not** require a running Qt application.
"""

from __future__ import annotations

import pytest
from sigima.objects import (
    CircularROI,
    PolygonalROI,
    RectangularROI,
    SegmentROI,
    create_image_roi,
    create_signal_roi,
)
from sigima.tests.data import create_multigaussian_image, create_paracetamol_signal

from sigimax.adapters_plotpy.converters import create_adapter_from_object
from sigimax.adapters_plotpy.objects.image import ImageObjPlotPyAdapter
from sigimax.adapters_plotpy.objects.signal import SignalObjPlotPyAdapter
from sigimax.adapters_plotpy.roi.image import (
    CircularROIPlotPyAdapter,
    ImageROIPlotPyAdapter,
    PolygonalROIPlotPyAdapter,
    RectangularROIPlotPyAdapter,
)
from sigimax.adapters_plotpy.roi.signal import (
    SegmentROIPlotPyAdapter,
    SignalROIPlotPyAdapter,
)

__all__ = [
    "test_factory_core_types",
    "test_factory_unsupported_type",
    "test_iterate_metadata_hook_default",
]


# ---------------------------------------------------------------------------
# test_factory_core_types
# ---------------------------------------------------------------------------

_EXPECTED_ADAPTERS = [
    # (factory_input_builder, expected_adapter_class)
    (create_paracetamol_signal, SignalObjPlotPyAdapter),
    (create_multigaussian_image, ImageObjPlotPyAdapter),
    (
        lambda: create_signal_roi([7.5, 10.0]),
        SignalROIPlotPyAdapter,
    ),
    (
        lambda: SegmentROI([7.5, 10.0], indices=False),
        SegmentROIPlotPyAdapter,
    ),
    (
        lambda: RectangularROI([10, 20, 30, 40], indices=False),
        RectangularROIPlotPyAdapter,
    ),
    (
        lambda: CircularROI([10, 20, 5], indices=False),
        CircularROIPlotPyAdapter,
    ),
    (
        lambda: PolygonalROI([0, 0, 10, 0, 5, 8], indices=False),
        PolygonalROIPlotPyAdapter,
    ),
    (
        lambda: create_image_roi("rectangle", [10, 20, 30, 40]),
        ImageROIPlotPyAdapter,
    ),
]


@pytest.mark.parametrize(
    "builder, expected_cls",
    _EXPECTED_ADAPTERS,
    ids=[
        "SignalObj",
        "ImageObj",
        "SignalROI",
        "SegmentROI",
        "RectangularROI",
        "CircularROI",
        "PolygonalROI",
        "ImageROI",
    ],
)
def test_factory_core_types(builder, expected_cls):
    """create_adapter_from_object() returns the correct adapter for each type."""
    obj = builder()
    adapter = create_adapter_from_object(obj)
    assert isinstance(adapter, expected_cls)


# ---------------------------------------------------------------------------
# test_factory_unsupported_type
# ---------------------------------------------------------------------------


def test_factory_unsupported_type():
    """create_adapter_from_object() raises TypeError for unknown types."""
    with pytest.raises(TypeError, match="Unsupported object type"):
        create_adapter_from_object("not a sigima object")


# ---------------------------------------------------------------------------
# test_iterate_metadata_hook_default
# ---------------------------------------------------------------------------


def test_iterate_metadata_hook_default():
    """BaseObjPlotPyAdapter.iterate_metadata_shape_items() yields nothing."""
    sig = create_paracetamol_signal()
    adapter = create_adapter_from_object(sig)
    items = list(adapter.iterate_metadata_shape_items("some_key", "val", "%g", True))
    assert not items
