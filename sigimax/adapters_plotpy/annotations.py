# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Annotation Adapter for PlotPy Integration
-----------------------------------------

This module bridges Sigima's format-agnostic annotation storage with PlotPy's
plot item system. It handles bidirectional conversion between:
- Sigima: list[dict] (JSON-serializable)
- PlotPy: list[AnnotatedShape] (plot items)
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import TYPE_CHECKING, Any

from guidata.io import JSONWriter
from plotpy.io import save_items
from sigima.objects.annotations import (
    GraphicalAnnotation,
    annotation_from_dict,
    annotation_to_dict,
    is_graphical_annotation_dict,
)
from sigima.objects.annotations.legacy_plotpy import (
    legacy_plotpy_payload_to_annotations,
)
from sigima.viz.annotation_plotpy import (
    annotation_to_plotpy_item,
    load_legacy_plotpy_items,
    plotpy_item_to_annotation,
)

if TYPE_CHECKING:
    from plotpy.items import AnnotatedShape
    from sigima.objects.base import BaseObj


_SOURCE_ATTRIBUTE = "_sigimax_annotation_source"
_PRESERVED_FIELDS = {"id", "metadata", "extensions"}


@dataclass
class _AnnotationItemSource:
    """Stored annotation represented by one PlotPy item."""

    object_id: int
    storage_index: int
    canonical: bool
    original: GraphicalAnnotation | None
    baseline: GraphicalAnnotation | None = None


class _LegacyPayloadObject:
    """Minimal object view used to load one historical PlotPy payload."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def get_annotations(self) -> list[dict[str, Any]]:
        """Return the single payload expected by Sigima's legacy loader."""
        return [self.payload]


class PlotPyAnnotationAdapter:
    """Adapter for converting between Sigima annotations and PlotPy items.

    This class provides the bridge between Sigima's generic annotation storage
    (list of dicts) and PlotPy's specific plot item format.

    Example:
        >>> from sigima.objects.signal.creation import create_signal
        >>> obj = create_signal("Test")
        >>> adapter = PlotPyAnnotationAdapter(obj)
        >>>
        >>> # Add PlotPy items
        >>> from plotpy.items import AnnotatedRectangle
        >>> rect = AnnotatedRectangle(0, 0, 10, 10)
        >>> adapter.add_items([rect])
        >>>
        >>> # Retrieve as PlotPy items
        >>> items = adapter.get_items()
        >>> len(items)
        1
    """

    def __init__(self, obj: BaseObj):
        """Initialize adapter with an object.

        Args:
            obj: Signal or image object with annotation support
        """
        self.obj = obj

    def get_items(self) -> list[AnnotatedShape]:
        """Get annotations as PlotPy items.

        Returns:
            List of PlotPy annotation items

        Notes:
            This method deserializes the JSON data stored in the object using
            PlotPy's load_items() function.
        """
        annotations = self.obj.get_annotations()
        if not annotations:
            return []

        items = []
        for index, ann_dict in enumerate(annotations):
            if is_graphical_annotation_dict(ann_dict):
                annotation = annotation_from_dict(ann_dict)
                item = annotation_to_plotpy_item(annotation)
                self._set_item_source(item, index, True, annotation)
                items.append(item)
            elif isinstance(ann_dict, dict) and "plotpy_json" in ann_dict:
                for item in self._load_legacy_payload(ann_dict):
                    self._set_item_source(
                        item, index, False, self._item_to_annotation(item)
                    )
                    items.append(item)

        return items

    @staticmethod
    def _serialize_plotpy_item(item: AnnotatedShape) -> dict[str, Any]:
        """Serialize an unsupported PlotPy item as an opaque legacy payload."""
        writer = JSONWriter(None)
        save_items(writer, [item])
        return {
            "type": "plotpy_item",
            "item_class": item.__class__.__name__,
            "plotpy_json": writer.get_json(),
        }

    @classmethod
    def _item_to_annotation(cls, item: AnnotatedShape) -> GraphicalAnnotation | None:
        """Convert a PlotPy item, including not-yet-initialized shapes."""
        try:
            annotation = plotpy_item_to_annotation(item)
        except (AttributeError, TypeError, ValueError):
            annotation = None
        if annotation is None:
            try:
                legacy_payload = cls._serialize_plotpy_item(item)
                [annotation] = legacy_plotpy_payload_to_annotations(legacy_payload)
            except (AttributeError, TypeError, ValueError):
                return None
        return annotation

    @classmethod
    def _item_to_payload(cls, item: AnnotatedShape) -> dict[str, Any]:
        """Convert a PlotPy item to canonical data when supported."""
        annotation = cls._item_to_annotation(item)
        if annotation is None:
            return cls._serialize_plotpy_item(item)
        return annotation_to_dict(annotation)

    @staticmethod
    def _load_legacy_payload(payload: dict[str, Any]) -> list[AnnotatedShape]:
        """Load one historical payload without modifying the source object."""
        return load_legacy_plotpy_items(_LegacyPayloadObject(payload))

    def _set_item_source(
        self,
        item: AnnotatedShape,
        storage_index: int,
        canonical: bool,
        original: GraphicalAnnotation | None,
    ) -> None:
        """Attach storage provenance and an initial PlotPy projection."""
        source = _AnnotationItemSource(
            object_id=id(self.obj),
            storage_index=storage_index,
            canonical=canonical,
            original=original,
        )
        setattr(item, _SOURCE_ATTRIBUTE, source)
        self.capture_item_reference(item)

    def _get_item_source(self, item: AnnotatedShape) -> _AnnotationItemSource | None:
        """Return provenance when *item* belongs to this object."""
        source = getattr(item, _SOURCE_ATTRIBUTE, None)
        if isinstance(source, _AnnotationItemSource) and source.object_id == id(
            self.obj
        ):
            return source
        return None

    def capture_item_reference(self, item: AnnotatedShape) -> None:
        """Capture the PlotPy state used as the edit comparison baseline."""
        source = self._get_item_source(item)
        if source is not None:
            source.baseline = self._item_to_annotation(item)

    def is_item_locked(self, item: AnnotatedShape) -> bool:
        """Return the persistent lock state represented by *item*."""
        source = self._get_item_source(item)
        if source is not None and source.original is not None:
            return source.original.locked
        return bool(item.is_readonly())

    def is_annotation_item(self, item: AnnotatedShape) -> bool:
        """Return whether *item* is a stored or newly created annotation."""
        if self._get_item_source(item) is not None:
            return True
        return not item.is_readonly() and self._item_to_annotation(item) is not None

    @staticmethod
    def _merge_edited_annotation(
        original: GraphicalAnnotation,
        baseline: GraphicalAnnotation | None,
        edited: GraphicalAnnotation,
    ) -> GraphicalAnnotation:
        """Apply only PlotPy-visible edits to a canonical annotation."""
        if baseline is None or type(original) is not type(edited):
            return original
        updates = {}
        for annotation_field in fields(original):
            name = annotation_field.name
            if name in _PRESERVED_FIELDS:
                continue
            if getattr(edited, name) != getattr(baseline, name):
                updates[name] = getattr(edited, name)
        return replace(original, **updates) if updates else original

    def set_items(self, items: list[AnnotatedShape]) -> None:
        """Set annotations from PlotPy items.

        Args:
            items: List of PlotPy annotation items

        Notes:
            This method serializes PlotPy items to JSON using PlotPy's
            save_items() function and stores them in the Sigima format.
        """
        stored = self.obj.get_annotations()
        sourced_items: dict[
            int, list[tuple[AnnotatedShape, _AnnotationItemSource]]
        ] = {}
        new_items = []
        for item in items:
            source = self._get_item_source(item)
            if source is None or source.storage_index >= len(stored):
                new_items.append(item)
            else:
                sourced_items.setdefault(source.storage_index, []).append(
                    (item, source)
                )

        output = []
        for index, payload in enumerate(stored):
            group = sourced_items.pop(index, [])
            if is_graphical_annotation_dict(payload):
                if not group:
                    continue
                item, source = group.pop(0)
                edited = self._item_to_annotation(item)
                if source.original is None or edited is None:
                    output.append(payload)
                else:
                    merged = self._merge_edited_annotation(
                        source.original, source.baseline, edited
                    )
                    output.append(
                        payload
                        if merged is source.original
                        else annotation_to_dict(merged)
                    )
                new_items.extend(item for item, _source in group)
            elif isinstance(payload, dict) and "plotpy_json" in payload:
                if not self._load_legacy_payload(payload):
                    output.append(payload)
                    continue
                converted = [self._item_to_annotation(item) for item, _source in group]
                if any(annotation is None for annotation in converted):
                    output.append(payload)
                else:
                    output.extend(
                        annotation_to_dict(annotation)
                        for annotation in converted
                        if annotation is not None
                    )
            else:
                output.append(payload)

        for group in sourced_items.values():
            new_items.extend(item for item, _source in group)
        output.extend(self._item_to_payload(item) for item in new_items)
        if output:
            self.obj.set_annotations(output)
        else:
            self.obj.clear_annotations()

    def add_items(self, items: list[AnnotatedShape]) -> None:
        """Add PlotPy items to existing annotations.

        Args:
            items: List of PlotPy annotation items to add
        """
        annotations = self.obj.get_annotations()
        annotations.extend(self._item_to_payload(item) for item in items)
        self.obj.set_annotations(annotations)

    def clear(self) -> None:
        """Clear all annotations."""
        self.obj.clear_annotations()
