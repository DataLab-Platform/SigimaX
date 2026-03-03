# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tier 4 — iterate_shape_items integration tests (offscreen Qt)
--------------------------------------------------------------

Tests that verify :meth:`iterate_shape_items` yields the expected plot items
when the underlying object carries ROI metadata, annotations, or neither.

Also includes the annotation roundtrip test (conceptually Tier 1 but needs Qt
because PlotPy items are QGraphicsObject subclasses).
"""

from __future__ import annotations

import numpy as np
from guidata.qthelpers import qt_app_context
from plotpy.items import AnnotatedRectangle, AnnotatedXRange
from sigima.objects import create_image_roi, create_signal_roi
from sigima.tests.data import create_multigaussian_image, create_paracetamol_signal

from sigimax.adapters_plotpy.converters import create_adapter_from_object

__all__ = [
    "test_annotations_roundtrip",
    "test_iterate_shape_items_empty",
    "test_iterate_shape_items_with_annotations",
    "test_iterate_shape_items_with_roi",
]


# ---------------------------------------------------------------------------
# Annotation roundtrip (Tier 1 concept, needs Qt for PlotPy items)
# ---------------------------------------------------------------------------


def test_annotations_roundtrip():
    """add_annotations_from_items() → get_items() preserves annotation data."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        adapter = create_adapter_from_object(sig)

        # Create a PlotPy annotation item
        x0, y0, x1, y1 = 1.0, 2.0, 5.0, 8.0
        rect = AnnotatedRectangle(x0, y0, x1, y1)

        # Store via adapter
        adapter.add_annotations_from_items([rect])
        assert sig.has_annotations()

        # Retrieve via annotation adapter
        recovered = adapter.annotation_adapter.get_items()
        assert len(recovered) == 1
        rec_rect = recovered[0]
        assert isinstance(rec_rect, AnnotatedRectangle)

        # Verify coordinates roundtrip
        r_x0, r_y0, r_x1, r_y1 = rec_rect.get_rect()
        np.testing.assert_allclose([r_x0, r_y0, r_x1, r_y1], [x0, y0, x1, y1])


# ---------------------------------------------------------------------------
# iterate_shape_items — with ROI
# ---------------------------------------------------------------------------


def test_iterate_shape_items_with_roi():
    """Object with ROI metadata → iterate_shape_items yields ROI plot items."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()

        # Attach a signal ROI (physical coordinates)
        xmin, xmax = float(sig.x[50]), float(sig.x[100])
        sig.roi = create_signal_roi([xmin, xmax])

        adapter = create_adapter_from_object(sig)
        items = list(adapter.iterate_shape_items(editable=False))

        # At least one item should have been produced for the ROI
        assert len(items) >= 1
        # The item should be an AnnotatedXRange (signal ROI)
        assert isinstance(items[0], AnnotatedXRange)


def test_iterate_shape_items_with_image_roi():
    """Image with ROI metadata → iterate_shape_items yields ROI plot items."""
    with qt_app_context(exec_loop=False):
        img = create_multigaussian_image()

        # Attach a rectangular ROI (physical coordinates)
        img.roi = create_image_roi("rectangle", [2.0, 3.0, 4.0, 5.0])

        adapter = create_adapter_from_object(img)
        items = list(adapter.iterate_shape_items(editable=False))

        assert len(items) >= 1
        assert isinstance(items[0], AnnotatedRectangle)


# ---------------------------------------------------------------------------
# iterate_shape_items — with annotations
# ---------------------------------------------------------------------------


def test_iterate_shape_items_with_annotations():
    """Object with annotations → iterate_shape_items yields annotation items."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        adapter = create_adapter_from_object(sig)

        # Add an annotation
        rect = AnnotatedRectangle(0.0, 0.0, 5.0, 5.0)
        adapter.add_annotations_from_items([rect])

        items = list(adapter.iterate_shape_items(editable=False))

        # Should contain at least the annotation item
        assert len(items) >= 1
        # Find the AnnotatedRectangle among yielded items
        rects = [it for it in items if isinstance(it, AnnotatedRectangle)]
        assert len(rects) == 1


# ---------------------------------------------------------------------------
# iterate_shape_items — empty
# ---------------------------------------------------------------------------


def test_iterate_shape_items_empty():
    """No metadata → iterate_shape_items yields nothing."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        # Ensure no ROI and no annotations
        sig.roi = None
        sig.annotations = ""

        adapter = create_adapter_from_object(sig)
        items = list(adapter.iterate_shape_items(editable=False))

        assert not items
