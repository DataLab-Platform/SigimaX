# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tier 3 — ROI conversion roundtrip tests (offscreen Qt)
-------------------------------------------------------

Tests that verify converting a Sigima ROI to a PlotPy plot item and back
preserves the original coordinates for both signal and image ROI types.
"""

from __future__ import annotations

import numpy as np
from guidata.qthelpers import qt_app_context
from sigima.objects import (
    CircularROI,
    PolygonalROI,
    RectangularROI,
    SegmentROI,
    create_image_roi,
    create_signal_roi,
)
from sigima.tests.data import create_multigaussian_image, create_paracetamol_signal

from sigimax.adapters_plotpy.converters import (
    plotitem_to_singleroi,
    singleroi_to_plotitem,
)

__all__ = [
    "test_image_roi_roundtrip_circle",
    "test_image_roi_roundtrip_polygon",
    "test_image_roi_roundtrip_rectangle",
    "test_signal_roi_roundtrip",
]


# ---------------------------------------------------------------------------
# Signal ROI roundtrip
# ---------------------------------------------------------------------------


def test_signal_roi_roundtrip():
    """Signal SegmentROI → plot item → SegmentROI preserves coordinates."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()

        # Use physical coordinates
        xmin, xmax = float(sig.x[50]), float(sig.x[100])
        roi = create_signal_roi([xmin, xmax])
        original = roi.get_single_roi(0)

        # ROI → plot item
        item = singleroi_to_plotitem(original, sig)

        # Plot item → ROI
        recovered = plotitem_to_singleroi(item, sig)

        assert isinstance(recovered, SegmentROI)
        orig_coords = original.get_physical_coords(sig)
        rec_coords = recovered.get_physical_coords(sig)
        np.testing.assert_allclose(rec_coords, orig_coords, rtol=1e-6)


# ---------------------------------------------------------------------------
# Image ROI roundtrip — Rectangle
# ---------------------------------------------------------------------------


def test_image_roi_roundtrip_rectangle():
    """Image RectangularROI → plot item → RectangularROI preserves coords."""
    with qt_app_context(exec_loop=False):
        img = create_multigaussian_image()

        roi = create_image_roi("rectangle", [2.0, 3.0, 4.0, 5.0])
        original = roi.get_single_roi(0)

        item = singleroi_to_plotitem(original, img)
        recovered = plotitem_to_singleroi(item, img)

        assert isinstance(recovered, RectangularROI)
        orig_coords = np.array(original.get_physical_coords(img), dtype=float)
        rec_coords = np.array(recovered.get_physical_coords(img), dtype=float)
        np.testing.assert_allclose(rec_coords, orig_coords, rtol=1e-6)


# ---------------------------------------------------------------------------
# Image ROI roundtrip — Circle
# ---------------------------------------------------------------------------


def test_image_roi_roundtrip_circle():
    """Image CircularROI → plot item → CircularROI preserves coords."""
    with qt_app_context(exec_loop=False):
        img = create_multigaussian_image()

        roi = create_image_roi("circle", [0.0, 0.0, 3.0])
        original = roi.get_single_roi(0)

        item = singleroi_to_plotitem(original, img)
        recovered = plotitem_to_singleroi(item, img)

        assert isinstance(recovered, CircularROI)
        orig_coords = np.array(original.get_physical_coords(img), dtype=float)
        rec_coords = np.array(recovered.get_physical_coords(img), dtype=float)
        np.testing.assert_allclose(rec_coords, orig_coords, rtol=1e-6)


# ---------------------------------------------------------------------------
# Image ROI roundtrip — Polygon
# ---------------------------------------------------------------------------


def test_image_roi_roundtrip_polygon():
    """Image PolygonalROI → plot item → PolygonalROI preserves coords."""
    with qt_app_context(exec_loop=False):
        img = create_multigaussian_image()

        coords = [0.0, 0.0, 5.0, 0.0, 5.0, 5.0, 0.0, 5.0]
        roi = create_image_roi("polygon", coords)
        original = roi.get_single_roi(0)

        item = singleroi_to_plotitem(original, img)
        recovered = plotitem_to_singleroi(item, img)

        assert isinstance(recovered, PolygonalROI)
        orig_coords = np.array(original.get_physical_coords(img), dtype=float)
        rec_coords = np.array(recovered.get_physical_coords(img), dtype=float)
        np.testing.assert_allclose(rec_coords, orig_coords, rtol=1e-6)
