# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tier 3 — ROI conversion roundtrip tests (offscreen Qt)
-------------------------------------------------------

Tests that verify converting a Sigima ROI to a PlotPy plot item and back
preserves the original coordinates for both signal and image ROI types.
"""

from __future__ import annotations

import numpy as np
import pytest
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

pytestmark = pytest.mark.gui

__all__ = [
    "test_image_roi_rectangle_info_in_indices",
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


# ---------------------------------------------------------------------------
# Image ROI tooltip — Rectangle in indices
# ---------------------------------------------------------------------------


def test_image_roi_rectangle_info_in_indices():
    """The tooltip of a rectangular ROI in indices shows the ROI pixels."""
    with qt_app_context(exec_loop=False):
        img = create_multigaussian_image()
        img.set_uniform_coords(0.5, 2.0, 10.0, -5.0)

        roi = create_image_roi("rectangle", [3, 4, 5, 6], indices=True)
        original = roi.get_single_roi(0)

        # The plot item goes from the outer edges of the ROI pixels
        item = singleroi_to_plotitem(original, img)
        info = item.info_callback(item)
        assert "= (3, 4)" in info, info
        assert "= 5 × 6" in info, info

        # Once moved by the user, the rectangle holds the pixels whose centers lie
        # inside it: columns 3 to 7 (index range 2.3 to 7.3) and rows 4 to 9
        # (index range 3.2 to 9.2), like the ROI itself
        x0, x1 = 10.0 + 0.5 * np.array([2.3, 7.3])
        y0, y1 = -5.0 + 2.0 * np.array([3.2, 9.2])
        item.set_rect(x0, y0, x1, y1)
        info = item.info_callback(item)
        assert "= (3, 4)" in info, info
        assert "= 5 × 6" in info, info
        roi = plotitem_to_singleroi(item, img)
        assert roi.get_indices_coords(img) == [3, 4, 5, 6]
