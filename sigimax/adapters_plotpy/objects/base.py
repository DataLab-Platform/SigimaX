# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
PlotPy Adapter Base Object Module
---------------------------------
"""

from __future__ import annotations

import abc
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
)

from guidata.dataset import update_dataset
from plotpy.items import (
    AnnotatedShape,
)
from sigima.objects.base import (
    ROI_KEY,
    TypeObj,
)

from sigimax.adapters_plotpy.annotations import PlotPyAnnotationAdapter
from sigimax.adapters_plotpy.base import (
    config_annotated_shape,
    set_plot_item_editable,
)
from sigimax.config import get_conf

if TYPE_CHECKING:
    from plotpy.items import CurveItem, MaskedXYImageItem
    from sigima.config import OptionField

TypePlotItem = TypeVar("TypePlotItem", bound="CurveItem | MaskedXYImageItem")


class BaseObjPlotPyAdapter(Generic[TypeObj, TypePlotItem]):
    """Object (signal/image) plot item adapter class"""

    DEFAULT_FMT = "s"  # This is overriden in children classes

    @property
    def conf_format(self) -> OptionField:
        """Config option field holding the numeric format string.

        Overridden in the image adapter to return the image-specific field.
        Resolved at runtime via ``get_conf()`` so the active (possibly
        derived-application) configuration is honoured.
        """
        return get_conf().sig_format

    def __init__(self, obj: TypeObj) -> None:
        """Initialize the adapter with the object.

        Args:
            obj: object (signal/image)
        """
        self.obj = obj
        # An empty format string in the configuration acts as a sentinel meaning
        # "use the adapter's type-appropriate DEFAULT_FMT".
        self.__default_options = {
            "format": "%" + (self.conf_format.get() or self.DEFAULT_FMT),
            "showlabel": get_conf().show_label.get(),
        }
        self.annotation_adapter = PlotPyAnnotationAdapter(obj)

    def get_obj_option(self, name: str) -> Any:
        """Get object option value.
        Args:
            name: option name

        Returns:
            Option value
        """
        default = self.__default_options[name]
        return self.obj.get_metadata_option(name, default)

    @abc.abstractmethod
    def make_item(self, update_from: TypePlotItem | None = None) -> TypePlotItem:
        """Make plot item from data.

        Args:
            update_from: update

        Returns:
            Plot item
        """

    @abc.abstractmethod
    def update_item(self, item: TypePlotItem, data_changed: bool = True) -> None:
        """Update plot item from data.

        Args:
            item: plot item
            data_changed: if True, data has changed
        """

    def add_annotations_from_items(self, items: list) -> None:
        """Add object annotations (annotation plot items).

        Args:
            items: annotation plot items
        """
        # Use the new annotation adapter
        self.annotation_adapter.add_items(items)

    def set_annotations_from_items(self, items: list) -> None:
        """Set object annotations (annotation plot items), replacing any existing ones.

        Args:
            items: annotation plot items
        """
        # Use the new annotation adapter
        self.annotation_adapter.set_items(items)

    @abc.abstractmethod
    def add_label_with_title(self, title: str | None = None) -> None:
        """Add label with title annotation

        Args:
            title: title (if None, use object title)
        """

    def iterate_metadata_shape_items(
        self, _key: str, _value: Any, _fmt: str, _lbl: bool
    ):
        """Hook: yield additional plot items for custom metadata entries.

        Override in subclasses to handle application-specific metadata
        (e.g., geometry results, table results). Called once for each metadata
        entry whose key is not ``ROI_KEY``.

        Args:
            key: metadata key
            value: metadata value
            fmt: numeric format string (e.g. "%.3f")
            lbl: whether to show labels

        Yields:
            Plot items for this metadata entry
        """
        return
        yield  # noqa: RET504 -- make this a generator

    def iterate_shape_items(self, editable: bool = False):
        """Iterate over shape items encoded in metadata (if any).

        Args:
            editable: if True, annotations are editable

        Yields:
            Plot item
        """
        fmt = self.get_obj_option("format")
        lbl = self.get_obj_option("showlabel")
        for key, value in self.obj.metadata.items():
            if key == ROI_KEY:
                roi = self.obj.roi
                if roi is not None:
                    # Delayed import to avoid circular dependency
                    # pylint: disable=import-outside-toplevel,cyclic-import
                    from sigimax.adapters_plotpy.roi.factory import create_roi_adapter

                    adapter = create_roi_adapter(roi)
                    yield from adapter.iterate_roi_items(
                        self.obj, fmt=fmt, lbl=lbl, editable=False
                    )
            else:
                yield from self.iterate_metadata_shape_items(key, value, fmt, lbl)
        # Use the new annotation adapter to get items
        if self.obj.has_annotations():
            for item in self.annotation_adapter.get_items():
                if isinstance(item, AnnotatedShape):
                    config_annotated_shape(item, fmt, lbl)
                set_plot_item_editable(item, editable)
                yield item

    def update_plot_item_parameters(self, item: TypePlotItem) -> None:
        """Update plot item parameters from object data/metadata

        Takes into account a subset of plot item parameters. Those parameters may
        have been overriden by object metadata entries or other object data. The goal
        is to update the plot item accordingly.

        This is *almost* the inverse operation of `update_metadata_from_plot_item`.

        Args:
            item: plot item
        """
        def_dict = get_conf().get_sigima_defaults(self.__class__.__name__[:3].lower())
        self.obj.set_metadata_options_defaults(def_dict, overwrite=False)

        # Subclasses have to override this method to update plot item parameters,
        # then call this implementation of the method to update plot item.
        update_dataset(item.param, self.obj.get_metadata_options())
        item.param.update_item(item)
        if item.selected:
            item.select()

    def update_metadata_from_plot_item(self, item: TypePlotItem) -> None:
        """Update metadata from plot item.

        Takes into account a subset of plot item parameters. Those parameters may
        have been modified by the user through the plot item GUI. The goal is to
        update the metadata accordingly.

        This is *almost* the inverse operation of `update_plot_item_parameters`.

        Args:
            item: plot item
        """
        def_dict = get_conf().get_sigima_defaults(self.__class__.__name__[:3].lower())
        for key in def_dict:
            if hasattr(item.param, key):  # In case the PlotPy version is not up-to-date
                self.obj.set_metadata_option(key, getattr(item.param, key))
