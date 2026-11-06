# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tier 3 — ROI conversion roundtrip tests (offscreen Qt)
-------------------------------------------------------

Tests that verify converting a Sigima ROI to a PlotPy plot item and back
preserves the original coordinates for both signal and image ROI types, as well
as their coordinate system (indices or physical coordinates) and inverse logic,
whether the plot item is moved or not.
"""

from __future__ import annotations

import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from plotpy.builder import make
from sigima.objects import (
    CircularROI,
    ImageObj,
    PolygonalROI,
    RectangularROI,
    SegmentROI,
    create_image,
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
    "test_image_roi_attributes_kept",
    "test_image_roi_rectangle_info_in_indices",
    "test_image_roi_roundtrip_circle",
    "test_image_roi_roundtrip_polygon",
    "test_image_roi_roundtrip_rectangle",
    "test_moved_roi_in_indices_without_object",
    "test_roi_from_new_item",
    "test_signal_roi_attributes_kept",
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
        assert roi.indices
        assert roi.get_indices_coords(img) == [3, 4, 5, 6]


# ---------------------------------------------------------------------------
# ROI attributes kept through plot items (coordinates in indices, inverse logic)
# ---------------------------------------------------------------------------

#: Image ROI coordinates (indices or physical) used by the following tests
IMAGE_ROI_CASES = [
    ("rectangle", [3, 4, 5, 6]),
    ("circle", [20, 15, 6]),
    ("polygon", [10, 10, 30, 10, 20, 30]),
]
#: Shift applied to moved ROIs, in pixels along X and Y
SHIFT = (2, 3)


def _small_image() -> ImageObj:
    """Return a small image with non-trivial physical coordinates

    Pixels are square: a circular ROI in indices has its radius along X, so that
    it is not a circle in pixels along Y with non-square pixels.
    """
    img = create_image("Test image", np.zeros((40, 50)))
    img.set_uniform_coords(0.5, 0.5, 10.0, -5.0)
    return img


def _shifted(geometry: str, coords: list[float], sx: float, sy: float) -> list[float]:
    """Return ROI coordinates shifted by (sx, sy)"""
    coords = np.array(coords, float)
    if geometry == "polygon":
        coords[::2] += sx
        coords[1::2] += sy
    else:
        coords[:2] += (sx, sy)
    return coords.tolist()


def _move(item, delta_x: float, delta_y: float) -> None:
    """Move a ROI plot item as the user does by dragging it"""
    item.shape.move_shape([0.0, 0.0], [delta_x, delta_y])


@pytest.mark.parametrize("inverse", [False, True])
@pytest.mark.parametrize("indices", [True, False])
@pytest.mark.parametrize("geometry, coords", IMAGE_ROI_CASES)
def test_image_roi_attributes_kept(
    geometry: str, coords: list[float], indices: bool, inverse: bool
):
    """An image ROI made into a plot item keeps its coordinate system and its
    inverse logic, whether the item is moved or not."""
    with qt_app_context(exec_loop=False):
        img = _small_image()
        roi = create_image_roi(geometry, coords, indices=indices, inverse=inverse)
        original = roi.get_single_roi(0)
        original.title = "My ROI"

        item = singleroi_to_plotitem(original, img)
        recovered = plotitem_to_singleroi(item, img)
        assert recovered == original
        assert recovered.title == "My ROI"

        # Move the item by whole pixels
        sx, sy = SHIFT
        _move(item, sx * img.dx, sy * img.dy)
        moved = plotitem_to_singleroi(item, img)
        assert type(moved) is type(original)
        assert moved.indices is indices
        assert moved.inverse is inverse
        if indices:
            expected = _shifted(geometry, coords, sx, sy)
            np.testing.assert_allclose(moved.coords, expected)
        else:
            expected = _shifted(geometry, coords, sx * img.dx, sy * img.dy)
            np.testing.assert_allclose(moved.coords, expected, atol=0.1 * img.dx)


@pytest.mark.parametrize("indices", [True, False])
def test_signal_roi_attributes_kept(indices: bool):
    """A signal ROI made into a plot item keeps its coordinate system, whether
    the item is moved or not."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        coords = [50, 100] if indices else [float(sig.x[50]), float(sig.x[100])]
        original = create_signal_roi(coords, indices=indices).get_single_roi(0)

        item = singleroi_to_plotitem(original, sig)
        assert plotitem_to_singleroi(item, sig) == original

        item.set_range(float(sig.x[60]), float(sig.x[110]))
        moved = plotitem_to_singleroi(item, sig)
        assert moved.indices is indices
        expected = [60, 110] if indices else [sig.x[60], sig.x[110]]
        np.testing.assert_allclose(moved.coords, expected, rtol=1e-6)


def test_roi_from_new_item():
    """A plot item which was not made from a ROI (e.g. drawn with a tool) gives a
    ROI in physical coordinates, with the default inverse logic."""
    with qt_app_context(exec_loop=False):
        img = _small_image()
        item = make.annotated_rectangle(12.0, -3.0, 14.0, 5.0)
        roi = plotitem_to_singleroi(item, img)
        assert isinstance(roi, RectangularROI)
        assert not roi.indices
        assert not roi.inverse
        np.testing.assert_allclose(roi.coords, [12.0, -3.0, 2.0, 8.0])


def test_moved_roi_in_indices_without_object():
    """Without object to convert coordinates, a moved ROI in indices is returned
    in physical coordinates, keeping its inverse logic."""
    with qt_app_context(exec_loop=False):
        img = _small_image()
        roi = create_image_roi("rectangle", [3, 4, 5, 6], indices=True, inverse=True)
        item = singleroi_to_plotitem(roi.get_single_roi(0), img)
        _move(item, img.dx, img.dy)
        moved = plotitem_to_singleroi(item)
        assert not moved.indices
        assert moved.inverse
        x0, y0, x1, y1 = item.get_rect()
        np.testing.assert_allclose(moved.coords, [x0, y0, x1 - x0, y1 - y0])
