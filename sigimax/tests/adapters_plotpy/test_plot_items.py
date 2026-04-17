# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tier 2 — Plot-item tests (offscreen Qt)
-----------------------------------------

Tests that exercise :meth:`make_item`, :meth:`update_item`, and the
plot-item-parameter roundtrip for signals and images.

Qt is required because PlotPy plot items are QGraphicsObject subclasses.
The tests use ``guidata.qthelpers.qt_app_context(exec_loop=False)`` so no
event-loop interaction is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from plotpy.items import CurveItem, MaskedXYImageItem
from sigima.tests.data import create_multigaussian_image, create_paracetamol_signal

from sigimax.adapters_plotpy.converters import create_adapter_from_object
from sigimax.adapters_plotpy.objects.image import ImageObjPlotPyAdapter
from sigimax.adapters_plotpy.objects.signal import SignalObjPlotPyAdapter

pytestmark = pytest.mark.gui

__all__ = [
    "test_image_make_item",
    "test_image_update_item",
    "test_signal_make_item",
    "test_signal_metadata_options",
    "test_signal_update_item",
]


# ---------------------------------------------------------------------------
# Signal — make_item
# ---------------------------------------------------------------------------


def test_signal_make_item():
    """SignalObjPlotPyAdapter.make_item() returns a CurveItem with correct data."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        adapter: SignalObjPlotPyAdapter = create_adapter_from_object(sig)
        item = adapter.make_item()

        assert isinstance(item, CurveItem)

        # Verify that the plot item carries the expected data
        x_item, y_item = item.get_data()[:2]
        x_obj, y_obj = sig.xydata[:2]
        np.testing.assert_array_equal(x_item, x_obj.real)
        np.testing.assert_array_equal(y_item, y_obj.real)


# ---------------------------------------------------------------------------
# Image — make_item
# ---------------------------------------------------------------------------


def test_image_make_item():
    """
    ImageObjPlotPyAdapter.make_item() returns a MaskedXYImageItem
    with correct data.
    """
    with qt_app_context(exec_loop=False):
        img = create_multigaussian_image()
        adapter: ImageObjPlotPyAdapter = create_adapter_from_object(img)
        item = adapter.make_item()

        assert isinstance(item, MaskedXYImageItem)

        # Verify that the underlying data matches
        item_data = item.data
        np.testing.assert_array_equal(item_data, img.data.real)


# ---------------------------------------------------------------------------
# Signal — update_item
# ---------------------------------------------------------------------------


def test_signal_update_item():
    """update_item() refreshes an existing CurveItem with new data."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        adapter: SignalObjPlotPyAdapter = create_adapter_from_object(sig)
        item = adapter.make_item()

        # Mutate the signal data
        sig.y = sig.y * 2.0
        adapter.update_item(item, data_changed=True)

        x_item, y_item = item.get_data()[:2]
        x_obj, y_obj = sig.xydata[:2]
        np.testing.assert_array_equal(x_item, x_obj.real)
        np.testing.assert_array_equal(y_item, y_obj.real)


# ---------------------------------------------------------------------------
# Image — update_item
# ---------------------------------------------------------------------------


def test_image_update_item():
    """update_item() refreshes an existing MaskedXYImageItem with new data."""
    with qt_app_context(exec_loop=False):
        img = create_multigaussian_image()
        adapter: ImageObjPlotPyAdapter = create_adapter_from_object(img)
        item = adapter.make_item()

        # Mutate the image data
        img.data = (img.data * 0.5).astype(img.data.dtype)

        # update_item() calls item.plot().update_colormap_axis() which requires
        # the item to be attached to a plot widget. Patch item.plot to avoid the
        # AttributeError in this headless test.

        item.plot = MagicMock()
        adapter.update_item(item, data_changed=True)

        np.testing.assert_array_equal(item.data, img.data.real)


# ---------------------------------------------------------------------------
# Signal — metadata options roundtrip
# ---------------------------------------------------------------------------


def test_signal_metadata_options():
    """update_plot_item_parameters ↔ update_metadata_from_plot_item preserves data."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        adapter: SignalObjPlotPyAdapter = create_adapter_from_object(sig)
        item = adapter.make_item()

        # Snapshot metadata that was written into the item
        adapter.update_plot_item_parameters(item)

        # Read metadata back from the item
        adapter.update_metadata_from_plot_item(item)

        # Create a fresh item from the same (now updated) object
        item2 = adapter.make_item()

        # The two items should have identical curve parameters
        assert item.param.label == item2.param.label
        assert item.param.line.color == item2.param.line.color
        assert item.param.line.style == item2.param.line.style
