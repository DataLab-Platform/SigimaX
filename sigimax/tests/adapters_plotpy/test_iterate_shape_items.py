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

import math

import numpy as np
import pytest
from guidata.io import JSONWriter
from guidata.qthelpers import qt_app_context
from plotpy.builder import make
from plotpy.io import save_items
from plotpy.items import AnnotatedRectangle, AnnotatedXRange
from sigima.objects import (
    Axis,
    CircleAnnotation,
    CursorAnnotation,
    CursorOrientation,
    EllipseAnnotation,
    PointAnnotation,
    PolygonAnnotation,
    PolylineAnnotation,
    RangeAnnotation,
    RectangleAnnotation,
    SegmentAnnotation,
    TextAnnotation,
    annotation_to_dict,
    create_image_roi,
    create_signal_roi,
)
from sigima.tests.data import create_multigaussian_image, create_paracetamol_signal

from sigimax.adapters_plotpy.converters import create_adapter_from_object

pytestmark = pytest.mark.gui

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
        [stored] = sig.get_annotations()
        assert stored["format"] == "sigima.annotation"
        assert "plotpy_json" not in stored

        # Retrieve via annotation adapter
        recovered = adapter.annotation_adapter.get_items()
        assert len(recovered) == 1
        rec_rect = recovered[0]
        assert isinstance(rec_rect, AnnotatedRectangle)

        # Verify coordinates roundtrip
        r_x0, r_y0, r_x1, r_y1 = rec_rect.get_rect()
        np.testing.assert_allclose([r_x0, r_y0, r_x1, r_y1], [x0, y0, x1, y1])


@pytest.mark.parametrize(
    "annotation",
    [
        PointAnnotation(x=1.0, y=2.0),
        SegmentAnnotation(x0=0.0, y0=0.0, x1=1.0, y1=1.0),
        RectangleAnnotation(
            x=1.0,
            y=2.0,
            width=3.0,
            height=4.0,
            angle=math.pi / 4,
        ),
        CircleAnnotation(cx=1.0, cy=2.0, radius=3.0),
        EllipseAnnotation(
            cx=1.0,
            cy=2.0,
            radius_x=3.0,
            radius_y=4.0,
            angle=math.pi / 6,
        ),
        PolylineAnnotation(points=((0.0, 0.0), (1.0, 1.0))),
        PolygonAnnotation(points=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))),
        TextAnnotation(text="Data", x=1.0, y=2.0),
        TextAnnotation(text="Axes", x=0.1, y=0.9, coordinate_space="axes"),
        CursorAnnotation(
            orientation=CursorOrientation.CROSSHAIR,
            position=(1.0, 2.0),
        ),
        RangeAnnotation(axis=Axis.X, start=1.0, end=2.0),
    ],
    ids=[
        "point",
        "segment",
        "rectangle",
        "circle",
        "ellipse",
        "polyline",
        "polygon",
        "text-data",
        "text-axes",
        "cursor",
        "range",
    ],
)
def test_all_canonical_primitives_roundtrip_without_rewrite(annotation):
    """Every canonical primitive survives a PlotPy no-op byte-for-byte."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        original = annotation_to_dict(annotation)
        sig.set_annotations([original])
        adapter = create_adapter_from_object(sig).annotation_adapter

        items = adapter.get_items()
        adapter.set_items(items)

        assert sig.get_annotations() == [original]


def test_canonical_annotation_edit_preserves_identity_and_opaque_data():
    """Canonical no-ops stay exact and edits retain non-PlotPy fields."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        opaque = {"consumer": "custom", "payload": {"keep": True}}
        annotation = RectangleAnnotation(
            x=3.0,
            y=5.0,
            width=4.0,
            height=6.0,
            locked=True,
            title="Reference",
            metadata={"owner": "test"},
            extensions={"vendor": {"keep": True}},
        )
        original = annotation_to_dict(annotation)
        sig.set_annotations([opaque, original])
        adapter = create_adapter_from_object(sig).annotation_adapter

        [item] = adapter.get_items()
        adapter.set_items([item])
        assert sig.get_annotations() == [opaque, original]

        item.set_rect(2.0, 3.0, 8.0, 11.0)
        adapter.set_items([item])

        preserved_opaque, edited = sig.get_annotations()
        assert preserved_opaque == opaque
        assert edited["id"] == original["id"]
        assert edited["metadata"] == original["metadata"]
        assert edited["extensions"] == original["extensions"]
        assert edited["locked"] is True
        assert edited["x"] == pytest.approx(5.0)
        assert edited["y"] == pytest.approx(7.0)
        assert edited["width"] == pytest.approx(6.0)
        assert edited["height"] == pytest.approx(8.0)


def test_legacy_annotations_migrate_only_on_write():
    """Reading is non-mutating while accepting the items migrates them."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        item = make.annotated_rectangle(1.0, 2.0, 5.0, 8.0, title="Legacy")
        writer = JSONWriter(None)
        save_items(writer, [item])
        legacy = {
            "type": "plotpy_item",
            "item_class": type(item).__name__,
            "plotpy_json": writer.get_json(),
        }
        opaque = {"consumer": "custom", "payload": {"keep": True}}
        sig.set_annotations([legacy, opaque])
        adapter = create_adapter_from_object(sig).annotation_adapter

        items = adapter.get_items()
        assert sig.get_annotations() == [legacy, opaque]

        adapter.set_items(items)
        migrated, preserved_opaque = sig.get_annotations()
        assert migrated["format"] == "sigima.annotation"
        assert "plotpy_json" not in migrated
        assert preserved_opaque == opaque


def test_unreadable_annotations_survive_replacement():
    """Replacing visible annotations preserves unreadable and opaque data."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        canonical = annotation_to_dict(
            RectangleAnnotation(x=3.0, y=5.0, width=4.0, height=6.0)
        )
        malformed = {"type": "plotpy_item", "plotpy_json": "{"}
        opaque = {"consumer": "custom", "payload": {"keep": True}}
        sig.set_annotations([canonical, malformed, opaque])
        adapter = create_adapter_from_object(sig).annotation_adapter

        assert len(adapter.get_items()) == 1
        adapter.set_items([])

        assert sig.get_annotations() == [malformed, opaque]


def test_partially_supported_legacy_group_is_preserved_atomically():
    """A legacy payload is not partly migrated when one item is unsupported."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        rectangle = make.annotated_rectangle(1.0, 2.0, 5.0, 8.0)
        curve = make.curve([0.0, 1.0], [1.0, 2.0])
        writer = JSONWriter(None)
        save_items(writer, [rectangle, curve])
        legacy = {
            "type": "plotpy_item",
            "plotpy_json": writer.get_json(),
        }
        sig.set_annotations([legacy])
        adapter = create_adapter_from_object(sig).annotation_adapter

        items = adapter.get_items()
        assert len(items) == 2
        adapter.set_items(items)

        assert sig.get_annotations() == [legacy]


def test_locked_annotation_remains_readonly_in_edit_mode():
    """Persistent annotation locks override the dialog edit mode."""
    with qt_app_context(exec_loop=False):
        sig = create_paracetamol_signal()
        sig.set_graphical_annotations(
            [
                RectangleAnnotation(width=1.0, height=1.0, locked=True),
                RectangleAnnotation(x=2.0, width=1.0, height=1.0),
            ]
        )
        adapter = create_adapter_from_object(sig)

        locked, editable = list(adapter.iterate_shape_items(editable=True))

        assert locked.is_readonly()
        assert not editable.is_readonly()
        assert adapter.annotation_adapter.is_annotation_item(locked)
        assert adapter.annotation_adapter.is_annotation_item(editable)


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
