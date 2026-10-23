# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX NeXus support: interpretation of ``NXdata`` groups

A NeXus ``NXdata`` group designates its plottable signal and the axes of each
signal dimension. :class:`NXdataNode` shows such a group as a single node of the
HDF5 browser, which is imported as a signal (1D) or an image (2D) with its axes,
units and uncertainties. Only metadata is read until the object is created, and
previews of large groups read one element out of a step along each dimension.

Supported conventions (NeXus data model, ``NXdata`` base class):

- ``@signal`` group attribute, or legacy ``signal=1`` dataset attribute
- ``@axes`` group attribute (``"."`` for a dimension without axis), with optional
  ``@<axis>_indices`` attributes, or legacy ``axes`` signal attribute; ``@axes``
  must give one entry per signal dimension
- axis datasets holding one real value per point, or bin edges (one more value),
  which are converted to bin centers; decreasing image axes are reversed, with
  the image, as images need increasing coordinates
- ``<signal>_errors`` (or legacy ``errors``) uncertainties of a 1D signal
- ``units`` and ``long_name`` dataset attributes
"""

from __future__ import annotations

import dataclasses
import math
import re

import h5py
import numpy as np
from guidata.utils.misc import to_string
from sigima.io.common.converters import convert_array_to_valid_dtype
from sigima.objects import (
    ImageObj,
    SignalObj,
    create_image,
    create_signal,
    make_experimental_source,
    set_experimental_source,
)

from sigimax.h5 import common, utils
from sigimax.h5.selection import preview_step

__all__ = [
    "NXAxis",
    "NXdataDescription",
    "NXdataNode",
    "describe_nxdata",
    "describe_signal",
]


def _text(value) -> str:
    """Return attribute value as text"""
    if isinstance(value, np.ndarray) and value.size == 1:
        value = value.flat[0]
    if isinstance(value, str) and re.search("[\udc80-\udcff]", value):
        # h5py decodes variable-length strings that are not UTF-8 with surrogates
        value = value.encode("utf-8", "surrogateescape")
    return to_string(value) if isinstance(value, (bytes, np.bytes_)) else str(value)


def _text_list(value) -> list[str]:
    """Return attribute value as a list of texts"""
    if isinstance(value, np.ndarray):
        return [_text(item) for item in value.flat]
    return [_text(value)]


@dataclasses.dataclass(frozen=True)
class NXAxis:
    """Axis of a signal dimension

    Args:
        name: axis dataset path, relative to the group
        size: number of values of the axis dataset
        edges: True if the axis holds bin edges (one value more than points)
        units: axis units
        label: axis label (``long_name`` attribute, or name)
    """

    name: str
    size: int
    edges: bool
    units: str
    label: str


@dataclasses.dataclass(frozen=True)
class NXdataDescription:
    """Description of an ``NXdata`` group, built from metadata only

    Args:
        path: group path
        signal: signal dataset path, relative to the group
        shape: signal shape
        dtype: signal data type
        axes: axis of each signal dimension (None if not defined)
        errors: uncertainties dataset name, if any
        units: signal units
        label: signal label
        problems: reasons why the signal cannot be imported as described
    """

    path: str
    signal: str
    shape: tuple[int, ...]
    dtype: np.dtype
    axes: tuple[NXAxis | None, ...]
    errors: str | None
    units: str
    label: str
    problems: tuple[str, ...]


def _is_nxdata(group: h5py.Group) -> bool:
    """Return True if group is an ``NXdata`` group"""
    return _text(group.attrs.get("NX_class", "")) == "NXdata"


def _find_signal(group: h5py.Group) -> tuple[str | None, list[str]]:
    """Return signal dataset name and axis names declared by an NXdata group"""
    if "signal" in group.attrs:
        signal = _text(group.attrs["signal"])
        axes = _text_list(group.attrs["axes"]) if "axes" in group.attrs else []
        return signal, axes
    for name, item in group.items():
        if isinstance(item, h5py.Dataset) and _text(item.attrs.get("signal", "")) in (
            "1",
            "True",
        ):
            axes = item.attrs.get("axes")
            names = (
                re.split(r"[:,\s]+", _text(axes).strip()) if axes is not None else []
            )
            return name, [axis for axis in names if axis]
    return None, []


def _axis_dimensions(
    group: h5py.Group, names: list[str], ndim: int
) -> tuple[list[str | None], list[str]]:
    """Return the axis name of each signal dimension, and the problems found"""
    axes: list[str | None] = [None] * ndim
    problems: list[str] = []
    if names and len(names) != ndim:
        problems.append(f"{len(names)} axes for {ndim} dimensions")
    for position, name in enumerate(names):
        if name == ".":
            continue
        indices = group.attrs.get(f"{name}_indices")
        if indices is None:
            if position >= ndim:
                continue  # Already reported as an axis count mismatch
            dims = [position]
        else:
            try:
                dims = [int(index) for index in np.ravel(indices)]
            except (TypeError, ValueError):
                problems.append(f"axis '{name}' has invalid indices")
                continue
        if len(dims) != 1:
            problems.append(f"axis '{name}' spans {len(dims)} dimensions")
        elif not 0 <= dims[0] < ndim:
            problems.append(f"axis '{name}' refers to missing dimension {dims[0]}")
        elif axes[dims[0]] is not None:
            problems.append(
                f"axes '{axes[dims[0]]}' and '{name}' describe dimension {dims[0]}"
            )
        else:
            axes[dims[0]] = name
    return axes, problems


def describe_nxdata(group: h5py.Group) -> NXdataDescription | None:
    """Describe an ``NXdata`` group, without reading its datasets

    Args:
        group: HDF5 group

    Returns:
        Description, or None if group is not an ``NXdata`` group with a numeric
        signal dataset
    """
    if not isinstance(group, h5py.Group) or not _is_nxdata(group):
        return None
    signal, names = _find_signal(group)
    dset = group.get(signal) if signal else None
    if not isinstance(dset, h5py.Dataset) or not dset.shape:
        return None
    axes, problems = _axis_dimensions(group, names, dset.ndim)
    desc = describe_signal(group, signal, axes, errors=(f"{signal}_errors", "errors"))
    if desc is None or not problems:
        return desc
    return dataclasses.replace(desc, problems=tuple(problems) + desc.problems)


def _is_real_number(dset: h5py.Dataset) -> bool:
    """Return True if dataset holds real numbers (integers or floats)"""
    return dset.dtype.kind in "iuf"


def describe_signal(
    group: h5py.Group,
    signal: str,
    axes: list[str | None],
    errors: tuple[str, ...] = (),
) -> NXdataDescription | None:
    """Describe a signal dataset of a group, without reading its datasets

    Args:
        group: HDF5 group
        signal: signal dataset path, relative to the group
        axes: axis dataset path of each signal dimension (None: no axis)
        errors: candidate uncertainties dataset paths; the first numeric one with
         the signal shape is used

    Returns:
        Description, or None if signal is not a numeric dataset
    """
    dset = group.get(signal)
    if (
        not isinstance(dset, h5py.Dataset)
        or not dset.shape
        or not utils.is_supported_num_dtype(dset)
    ):
        return None
    problems: list[str] = []
    if len(axes) != dset.ndim:
        problems.append(f"{len(axes)} axes for {dset.ndim} dimensions")
        axes = (list(axes) + [None] * dset.ndim)[: dset.ndim]
    axis_descs: list[NXAxis | None] = []
    for dim, name in enumerate(axes):
        axis_dset = group.get(name) if name else None
        if name is None:
            axis_descs.append(None)
        elif not isinstance(axis_dset, h5py.Dataset) or axis_dset.ndim != 1:
            problems.append(f"axis '{name}' is not a 1D dataset")
            axis_descs.append(None)
        elif not _is_real_number(axis_dset):
            problems.append(f"axis '{name}' does not hold real numbers")
            axis_descs.append(None)
        elif axis_dset.shape[0] not in (dset.shape[dim], dset.shape[dim] + 1):
            problems.append(
                f"axis '{name}' has {axis_dset.shape[0]} values "
                f"for {dset.shape[dim]} points"
            )
            axis_descs.append(None)
        else:
            axis_descs.append(
                NXAxis(
                    name=name,
                    size=axis_dset.shape[0],
                    edges=axis_dset.shape[0] == dset.shape[dim] + 1,
                    units=_text(axis_dset.attrs.get("units", "")).strip(),
                    label=_text(
                        axis_dset.attrs.get("long_name", name.split("/")[-1])
                    ).strip(),
                )
            )
    found = None
    for name in errors:
        candidate = group.get(name)
        if (
            isinstance(candidate, h5py.Dataset)
            and candidate.shape == dset.shape
            and _is_real_number(candidate)
        ):
            found = name
            break
    return NXdataDescription(
        path=group.name,
        signal=signal,
        shape=dset.shape,
        dtype=dset.dtype,
        axes=tuple(axis_descs),
        errors=found,
        units=_text(dset.attrs.get("units", "")).strip(),
        label=_text(dset.attrs.get("long_name", signal.split("/")[-1])).strip(),
        problems=tuple(problems),
    )


def _read_axis(group: h5py.Group, axis: NXAxis) -> tuple[np.ndarray, np.dtype]:
    """Return axis values, at bin centers, and the data type of the axis dataset"""
    dset = group[axis.name]
    values = np.asarray(dset[()], dtype=float)
    if axis.edges:
        values = (values[:-1] + values[1:]) / 2
    return values, dset.dtype


def _is_uniform(values: np.ndarray, dtype: np.dtype) -> bool:
    """Return True if monotonic values are evenly spaced, within the precision of
    the data type they were stored with"""
    if values.size < 3:
        return True
    eps = np.finfo(dtype if dtype.kind == "f" else float).eps
    tolerance = 4 * float(eps) * max(abs(values[0]), abs(values[-1]))
    expected = np.linspace(values[0], values[-1], values.size)
    return bool(np.all(np.abs(values - expected) <= tolerance))


def _is_decreasing(values: np.ndarray, name: str) -> bool:
    """Return True if axis values are strictly decreasing, False if they are
    strictly increasing

    Raises:
        ValueError: if values are not strictly monotonic
    """
    steps = np.diff(values)
    if np.all(steps > 0):
        return False
    if np.all(steps < 0):
        return True
    raise ValueError(f"Axis '{name}' is not strictly monotonic")


def _image_axis(
    group: h5py.Group, axis: NXAxis | None, size: int, step: int = 1
) -> tuple[np.ndarray, np.dtype, bool]:
    """Return image axis values in increasing order, the data type they were
    stored with, and True if they were reversed

    Args:
        group: NXdata group
        axis: axis description, or None for a dimension without axis
        size: number of points along the dimension
        step: step between the returned values (to read a decimated preview)

    Raises:
        ValueError: if axis values are not strictly monotonic
    """
    if axis is None:
        return np.arange(0, size, step, dtype=float), np.dtype(float), False
    values, dtype = _read_axis(group, axis)
    reverse = _is_decreasing(values, axis.name)
    values = values[::step]
    return (values[::-1] if reverse else values), dtype, reverse


def _set_image_coords(
    obj: ImageObj,
    xaxis: tuple[np.ndarray, np.dtype],
    yaxis: tuple[np.ndarray, np.dtype],
) -> None:
    """Set image coordinates: uniform if axes are evenly spaced, else non-uniform

    Args:
        obj: image object
        xaxis: X axis values in increasing order, and their stored data type
        yaxis: Y axis values in increasing order, and their stored data type
    """
    (xc, xdtype), (yc, ydtype) = xaxis, yaxis
    if _is_uniform(xc, xdtype) and _is_uniform(yc, ydtype):
        dx = float(xc[-1] - xc[0]) / (xc.size - 1) if xc.size > 1 else 1.0
        dy = float(yc[-1] - yc[0]) / (yc.size - 1) if yc.size > 1 else 1.0
        obj.set_uniform_coords(dx, dy, float(xc[0]), float(yc[0]))
    else:
        obj.set_coords(xc, yc)


class NXdataNode(common.GroupNode):
    """Node for NeXus ``NXdata`` groups, imported as a signal or an image

    Args:
        h5file: HDF5 file
        dname: group path
        nxdata: signal description (default: described from ``NXdata`` attributes)
    """

    #: Kind of the experimental source of the imported objects
    SOURCE_KIND = "nexus"

    def __init__(self, h5file, dname, nxdata: NXdataDescription | None = None):
        super().__init__(h5file, dname)
        self.nxdata = describe_nxdata(self.dset) if nxdata is None else nxdata
        self.text_prefix = "NXdata"

    @classmethod
    def match(cls, dset):
        """Return True if h5 group is an ``NXdata`` group with a numeric signal"""
        return describe_nxdata(dset) is not None

    def is_supported(self) -> bool:
        """Return True if the signal is 1D or 2D and its axes are valid"""
        desc = self.nxdata
        return (
            not desc.problems
            and len(desc.shape) in (1, 2)
            and int(np.prod(desc.shape)) > 1
        )

    @property
    def icon_name(self):
        """Icon name associated to node"""
        if self.is_supported():
            return "signal.svg" if len(self.nxdata.shape) == 1 else "image.svg"
        return "h5group.svg"

    @property
    def shape_str(self):
        """Return string representation of node shape"""
        return " x ".join([str(size) for size in self.nxdata.shape])

    @property
    def dtype_str(self):
        """Return string representation of node data type"""
        return str(self.nxdata.dtype)

    @property
    def text(self):
        """Return node textual representation"""
        desc = self.nxdata
        names = [axis.name if axis else "." for axis in desc.axes]
        text = f"{self.text_prefix}: {desc.signal} ({', '.join(names)})"
        if desc.problems:
            text += " - " + "; ".join(desc.problems)
        return text

    @property
    def description(self):
        """Return node description"""
        return self.text

    def source_details(self) -> dict | None:
        """Return the details of the experimental source of the imported object
        (None: no details)"""
        return None

    def make_source(self, conversions: list[str]) -> dict:
        """Return the experimental source of the imported object

        Dimensions without axis are recorded as ``"."``, as in NeXus ``@axes``.
        """
        desc = self.nxdata
        return make_experimental_source(
            self.SOURCE_KIND,
            self.h5file.filename,
            entry=desc.path,
            selection={
                "signal": desc.signal,
                "axes": [axis.name if axis else "." for axis in desc.axes],
            },
            conversions=conversions or None,
            details=self.source_details(),
        )

    def create_native_object(self):
        """Create signal or image object from the ``NXdata`` group"""
        if not self.is_supported():
            return None
        obj, conversions = self._build_object(1)
        set_experimental_source(obj, self.make_source(conversions))
        return obj

    def create_preview_object(self, max_items: int):
        """Return the native object, or a decimated one if the signal has more
        than ``max_items`` elements (only the read elements of its axes are kept)

        Args:
            max_items: maximum number of signal elements to read
        """
        if not self.is_supported():
            return None
        shape = self.nxdata.shape
        if math.prod(shape) <= max_items:
            return self.get_native_object()
        obj, _conversions = self._build_object(preview_step(shape, max_items))
        return obj

    def _build_object(self, step: int) -> tuple[SignalObj | ImageObj, list[str]]:
        """Create signal or image object from the ``NXdata`` group, reading one
        element out of ``step`` along each dimension

        Returns:
            Object and conversions applied to the source values
        """
        desc = self.nxdata
        dset = self.dset[desc.signal]
        data = dset[(slice(None, None, step),) * dset.ndim]
        conversions = [
            f"axis '{axis.name}': bin edges -> bin centers"
            for axis in desc.axes
            if axis is not None and axis.edges
        ]
        if len(desc.shape) == 1:
            return self._build_signal(data, step), conversions
        return self._build_image(data, step, conversions), conversions

    def _build_signal(self, data: np.ndarray, step: int) -> SignalObj:
        """Create the signal object of a 1D ``NXdata`` group

        Args:
            data: signal values, read with step
            step: step between the read elements

        Returns:
            Signal object
        """
        desc, group = self.nxdata, self.dset
        axis = desc.axes[0]
        x = np.arange(0, desc.shape[0], step, dtype=float)
        if axis is not None:
            x = _read_axis(group, axis)[0][::step]
        dy = None
        if desc.errors is not None:
            dy = np.asarray(group[desc.errors][::step], dtype=float)
        y = common.to_signal_data(data)
        obj = create_signal(self.object_title, x, y, dy=dy)
        obj.ylabel, obj.yunit = desc.label, desc.units
        if axis is not None:
            obj.xlabel, obj.xunit = axis.label, axis.units
        return obj

    def _build_image(
        self, data: np.ndarray, step: int, conversions: list[str]
    ) -> ImageObj:
        """Create the image object of a 2D ``NXdata`` group

        Args:
            data: image values, read with step along both dimensions
            step: step between the read elements
            conversions: conversions applied to the source values, completed with
             the ones applied to the image

        Returns:
            Image object
        """
        desc, group = self.nxdata, self.dset
        yaxis, xaxis = desc.axes
        ny, nx = desc.shape
        # PlotPy images need increasing coordinates: decreasing axes are reversed
        xc, xdtype, xreversed = _image_axis(group, xaxis, nx, step)
        yc, ydtype, yreversed = _image_axis(group, yaxis, ny, step)
        for axis, reverse, dim in ((xaxis, xreversed, 1), (yaxis, yreversed, 0)):
            if reverse:
                data = np.flip(data, axis=dim)
                conversions.append(f"axis '{axis.name}': reversed to increasing order")
        obj = create_image(
            self.object_title,
            convert_array_to_valid_dtype(
                np.ascontiguousarray(data), ImageObj.VALID_DTYPES
            ),
        )
        obj.zlabel, obj.zunit = desc.label, desc.units
        _set_image_coords(obj, (xc, xdtype), (yc, ydtype))
        if xaxis is not None:
            obj.xlabel, obj.xunit = xaxis.label, xaxis.units
        if yaxis is not None:
            obj.ylabel, obj.yunit = yaxis.label, yaxis.units
        if desc.errors is not None:
            conversions.append("uncertainties not imported (image)")
        return obj


common.NODE_FACTORY.register(NXdataNode, is_generic=True)
