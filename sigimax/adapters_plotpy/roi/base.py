# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
PlotPy Adapter Base ROI Module
------------------------------
"""

from __future__ import annotations

import abc
import copy
import weakref
from typing import TYPE_CHECKING, Any, Generic, Iterator, Literal, TypeVar

import numpy as np
from plotpy.items import AnnotatedShape
from sigima.objects.base import (
    BaseROI,
    TypeObj,
    TypeROI,
    TypeROIParam,
    TypeSingleROI,
    get_generic_roi_title,
)

from sigimax.adapters_plotpy.base import config_annotated_shape

if TYPE_CHECKING:
    from plotpy.items import (
        AnnotatedCircle,
        AnnotatedPolygon,
        AnnotatedRectangle,
        AnnotatedXRange,
    )

TypeROIItem = TypeVar(
    "TypeROIItem",
    bound="AnnotatedXRange | AnnotatedPolygon | AnnotatedRectangle | AnnotatedCircle",
)

#: Single ROI from which each plot item was made by ``to_plot_item``, with the
#: coordinates of the item at that time, to restore the ROI attributes that plot
#: items do not represent (coordinates in indices, inverse logic...)
_ITEM_ORIGINS: weakref.WeakKeyDictionary[Any, tuple[Any, np.ndarray]] = (
    weakref.WeakKeyDictionary()
)


class BaseSingleROIPlotPyAdapter(Generic[TypeSingleROI, TypeROIItem], abc.ABC):
    """Base class for single ROI plot item adapter

    Args:
        single_roi: single ROI object
    """

    #: Single ROI class
    ROI_CLASS: type[TypeSingleROI]

    def __init__(self, single_roi: TypeSingleROI) -> None:
        self.single_roi = single_roi

    @abc.abstractmethod
    def to_plot_item(self, obj: TypeObj) -> TypeROIItem:
        """Make ROI plot item from ROI.

        Implementations must return the item through :meth:`_remember_item`.

        Args:
            obj: object (signal/image), for physical-indices coordinates conversion

        Returns:
            Plot item
        """

    def _remember_item(self, item: TypeROIItem) -> TypeROIItem:
        """Remember the single ROI from which a plot item was made

        Args:
            item: plot item made from the single ROI

        Returns:
            The plot item
        """
        _ITEM_ORIGINS[item] = (
            copy.deepcopy(self.single_roi),
            np.array(self._item_coords(item), float),
        )
        return item

    @classmethod
    @abc.abstractmethod
    def _item_coords(cls, item: TypeROIItem) -> list[float]:
        """Return the physical coordinates of the ROI drawn by a plot item

        Args:
            item: plot item

        Returns:
            Physical coordinates, in the order of the single ROI coordinates
        """

    @classmethod
    @abc.abstractmethod
    def _round_coords(cls, obj: TypeObj, coords: list[float]) -> list[float]:
        """Round physical coordinates to a precision suited to the object

        Args:
            obj: object (signal/image)
            coords: physical coordinates

        Returns:
            Rounded coordinates
        """

    @classmethod
    def from_plot_item(
        cls, item: TypeROIItem, obj: TypeObj | None = None
    ) -> TypeSingleROI:
        """Create single ROI from plot item

        A plot item made from a single ROI (see :meth:`to_plot_item`) gives back
        this ROI if it was not moved, with the title of the item. Once moved, the
        ROI keeps its attributes (e.g. the inverse logic of image ROIs) and its
        coordinate system: coordinates in indices are converted with ``obj``,
        following the ROI rules (e.g. the pixels whose centers lie inside a
        rectangle). Other items (e.g. drawn with a tool) give a ROI in physical
        coordinates.

        Args:
            item: plot item
            obj: object (signal/image), to round physical coordinates and convert
             them to indices. Without it, a moved ROI in indices is returned in
             physical coordinates.

        Returns:
            Single ROI
        """
        coords = cls._item_coords(item)
        title = str(item.title().text())
        original, initial = _ITEM_ORIGINS.get(item, (None, None))
        if original is None:
            if obj is not None:
                coords = cls._round_coords(obj, coords)
            return cls.ROI_CLASS(coords, False, title)
        roi = copy.deepcopy(original)
        roi.title = title
        if np.allclose(coords, initial, rtol=1e-12, atol=1e-12):
            return roi
        if roi.indices and obj is not None:
            roi.set_physical_coords(obj, np.array(coords, float))
        else:
            if obj is not None:
                coords = cls._round_coords(obj, coords)
            roi.indices = False
            roi.coords = np.array(coords, float)
        roi.check_coords()
        return roi


def configure_roi_item(
    item: TypeROIItem,
    fmt: str,
    lbl: bool,
    editable: bool,
    option: Literal["s", "i"],
):
    """Configure ROI plot item.

    Args:
        item: plot item
        fmt: numeric format (e.g. "%.3f")
        lbl: if True, show shape labels
        editable: if True, make shape editable
        option: shape style option ("s" for signal, "i" for image)

    Returns:
        Plot item
    """
    option += "/" + ("editable" if editable else "readonly")
    if not editable:
        if isinstance(item, AnnotatedShape):
            config_annotated_shape(
                item, fmt, lbl, "roi", option, show_computations=editable
            )
        item.set_movable(False)
        item.set_resizable(False)
        item.set_readonly(True)
    item.set_style("roi", option)
    return item


class BaseROIPlotPyAdapter(Generic[TypeROI], abc.ABC):
    """ROI plot item adapter class

    Args:
        roi: ROI object
    """

    def __init__(self, roi: BaseROI[TypeObj, TypeSingleROI, TypeROIParam]) -> None:
        self.roi = roi

    @abc.abstractmethod
    def to_plot_item(self, single_roi: TypeSingleROI, obj: TypeObj) -> TypeROIItem:
        """Make ROI plot item from single ROI

        Args:
            single_roi: single ROI object
            obj: object (signal/image), for physical-indices coordinates conversion

        Returns:
            Plot item
        """

    def iterate_roi_items(
        self, obj: TypeObj, fmt: str, lbl: bool, editable: bool = True
    ) -> Iterator[TypeROIItem]:
        """Iterate over ROI plot items associated to each single ROI composing
        the object.

        Args:
            obj: object (signal/image), for physical-indices coordinates conversion
            fmt: format string
            lbl: if True, add label
            editable: if True, ROI is editable

        Yields:
            Plot item
        """
        for index, single_roi in enumerate(self.roi.single_rois):
            roi_item = self.to_plot_item(single_roi, obj)
            item = configure_roi_item(
                roi_item, fmt, lbl, editable, option=self.roi.PREFIX
            )
            item.setTitle(single_roi.title or get_generic_roi_title(index))
            yield item
