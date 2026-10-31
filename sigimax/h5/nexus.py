# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX NeXus support: interpretation of ``NXdata`` groups

A NeXus ``NXdata`` group designates its plottable signal and the axes of each
signal dimension. :class:`NXdataNode` shows such a group as a single node of the
HDF5 browser, which is imported as a signal (1D) or an image (2D) with its axes,
units and uncertainties, or, for signals of three dimensions or more, through a
view: one signal or image per frame (:mod:`sigimax.h5.views`). Auxiliary signals
of the group are shown as nodes of their own (:class:`AuxiliarySignalNode`).
Only metadata is read until the object is created, and previews of large groups
read one element out of a step along each dimension.

Supported conventions (NeXus data model, ``NXdata`` base class):

- ``@signal`` group attribute, or legacy ``signal=1`` dataset attribute
- ``@axes`` group attribute (``"."`` for a dimension without axis), with optional
  ``@<axis>_indices`` attributes, or legacy ``axes`` signal attribute; ``@axes``
  must give one entry per signal dimension
- without ``@axes``, legacy ``axis`` attributes of axis datasets (dimension number,
  from 1), the dataset with the lowest ``primary`` attribute being preferred for
  each dimension; an axis applies to a dimension only if its size fits
- auxiliary signals: ``@auxiliary_signals`` group attribute, and the other
  datasets having a legacy ``signal`` attribute (whatever its value), with the
  axes that fit their dimensions
- axis datasets holding one real value per point, or bin edges (one more value),
  which are converted to bin centers; decreasing image axes are reversed, with
  the image, as images need increasing coordinates
- image axes evenly spaced within :data:`UNIFORM_AXIS_TOLERANCE` are imported as
  uniform coordinates, their maximum deviation being recorded as a conversion;
  other image axes keep their stored coordinates
- ``<signal>_errors`` (or legacy ``errors``) uncertainties of a 1D signal
- ``units`` and ``long_name`` dataset attributes, ``interpretation`` signal
  attribute (default view of multidimensional signals)
- ``@default`` attributes of the file and its entries, designating the default
  ``NXdata`` group (:func:`default_nxdata_path`)
- ``title``, ``start_time`` and ``end_time`` of the ``NXentry`` group, recorded in
  the origin of the imported objects

Signals compressed with a filter that HDF5 cannot apply are reported as problems.
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
from sigimax.h5.selection import NDSelection, preview_step, read_selection
from sigimax.h5.views import NDViewMixin

__all__ = [
    "UNIFORM_AXIS_TOLERANCE",
    "AuxiliarySignalNode",
    "NXAxis",
    "NXdataDescription",
    "NXdataNode",
    "default_nxdata_path",
    "describe_auxiliary_signals",
    "describe_nxdata",
    "describe_signal",
    "entry_information",
]

#: Maximum deviation of image axis values from even spacing for the axis to be
#: imported as uniform coordinates, in units in the last place (ULP) of the data
#: type they were stored with, at the largest axis magnitude: evenly spaced values
#: computed in their storage precision deviate by up to about 2 ULP
UNIFORM_AXIS_TOLERANCE = 2.5


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


def _attr_rank(item: h5py.Dataset, name: str) -> int | None:
    """Return a positive integer attribute (legacy ``signal``, ``axis`` or
    ``primary``), or None if it is missing or invalid; ``True`` stands for 1"""
    if name not in item.attrs:
        return None
    text = _text(item.attrs[name]).strip()
    if text == "True":
        return 1
    try:
        value = float(text)
    except ValueError:
        return None
    return int(value) if value.is_integer() and value >= 1 else None


def _natural_key(name: str) -> list:
    """Return sort key ordering numbered names numerically"""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


def _legacy_axes(group: h5py.Group, shape: tuple[int, ...]) -> list[str | None]:
    """Return the axis of each signal dimension designated by legacy ``axis``
    attributes (dimension number, from 1), or None

    An axis applies to a dimension only if it holds one real value per point (or
    bin edges); among the axes of a dimension, the one with the lowest ``primary``
    attribute is preferred.
    """
    candidates: dict[int, list[tuple[float, str]]] = {}
    for name, item in group.items():
        if not isinstance(item, h5py.Dataset) or "axis" not in item.attrs:
            continue
        number = _attr_rank(item, "axis")
        if number is None or number > len(shape) or item.ndim != 1:
            continue
        size = shape[number - 1]
        if not _is_real_number(item) or item.shape[0] not in (size, size + 1):
            continue
        primary = _attr_rank(item, "primary")
        rank = math.inf if primary is None else primary
        candidates.setdefault(number - 1, []).append((rank, name))
    return [
        min(candidates[dim])[1] if dim in candidates else None
        for dim in range(len(shape))
    ]


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
    if names:
        axes, problems = _axis_dimensions(group, names, dset.ndim)
    else:
        axes, problems = _legacy_axes(group, dset.shape), []
    desc = describe_signal(group, signal, axes, errors=(f"{signal}_errors", "errors"))
    if desc is None or not problems:
        return desc
    return dataclasses.replace(desc, problems=tuple(problems) + desc.problems)


def describe_auxiliary_signals(
    group: h5py.Group, main: NXdataDescription | None = None
) -> list[NXdataDescription]:
    """Describe the auxiliary signals of an ``NXdata`` group, without reading its
    datasets

    Auxiliary signals are those of the ``@auxiliary_signals`` group attribute,
    then the datasets having a legacy ``signal`` attribute, by attribute value and
    name, except the signal of the group. They have the axes of the signal if they
    have its shape, otherwise the axes designated by legacy ``axis`` attributes
    that fit their dimensions.

    Args:
        group: HDF5 group
        main: description of the group (default: described from its attributes)

    Returns:
        Descriptions of the numeric auxiliary signals
    """
    main = describe_nxdata(group) if main is None else main
    if main is None:
        return []
    names: list[str] = []
    if "auxiliary_signals" in group.attrs:
        names.extend(_text_list(group.attrs["auxiliary_signals"]))
    legacy = []
    for name, item in group.items():
        if isinstance(item, h5py.Dataset):
            rank = _attr_rank(item, "signal")
            if rank is not None:
                legacy.append((rank, _natural_key(name), name))
    names.extend(name for *_key, name in sorted(legacy) if name not in names)
    main_axes = [axis.name if axis is not None else None for axis in main.axes]
    descs = []
    for name in names:
        dset = group.get(name)
        if name == main.signal or not isinstance(dset, h5py.Dataset) or not dset.shape:
            continue
        if dset.shape == main.shape and not main.problems:
            axes = main_axes
        else:
            axes = _legacy_axes(group, dset.shape)
        desc = describe_signal(group, name, axes, errors=(f"{name}_errors",))
        if desc is not None:
            descs.append(desc)
    return descs


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
    missing = utils.unavailable_filters(dset)
    if missing:
        problems.append("compressed with unavailable filter: " + ", ".join(missing))
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
                    label=_text(axis_dset.attrs.get("long_name", "")).strip()
                    or name.split("/")[-1],
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
        label=_text(dset.attrs.get("long_name", "")).strip() or signal.split("/")[-1],
        problems=tuple(problems),
    )


def _read_axis(
    group: h5py.Group, axis: NXAxis, step: int = 1
) -> tuple[np.ndarray, np.dtype]:
    """Return axis values, at bin centers, and the data type of the axis dataset

    Args:
        group: NXdata group
        axis: axis description
        step: step between the returned values (to read a decimated preview): only
         the read values are loaded, giving the same values as a full read
         followed by ``[::step]``
    """
    dset = group[axis.name]
    if step == 1:
        values = np.asarray(dset[()], dtype=float)
        if axis.edges:
            values = (values[:-1] + values[1:]) / 2
    elif axis.edges:
        # Only the edges bounding the returned bins are read
        nbins = dset.shape[0] - 1
        lower = np.asarray(dset[0:nbins:step], dtype=float)
        upper = np.asarray(dset[1 : nbins + 1 : step], dtype=float)
        values = (lower + upper) / 2
    else:
        values = np.asarray(dset[::step], dtype=float)
    return values, dset.dtype


def _precision_type(dtype: np.dtype) -> type[np.floating]:
    """Return the floating type giving the precision of axis values stored with
    ``dtype`` (axis values are read as float64)"""
    return dtype.type if dtype.kind == "f" and dtype.itemsize < 8 else np.float64


def _uniform_deviation(values: np.ndarray, dtype: np.dtype) -> tuple[float, float]:
    """Return the maximum deviation of monotonic values from even spacing, and
    this deviation in units in the last place (ULP) of the data type they were
    stored with, at the largest axis magnitude"""
    if values.size < 3:
        return 0.0, 0.0
    expected = np.linspace(values[0], values[-1], values.size)
    deviation = float(np.max(np.abs(values - expected)))
    bound = max(abs(values[0]), abs(values[-1]))
    return deviation, deviation / float(np.spacing(_precision_type(dtype)(bound)))


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
    # Read entirely, even for a preview, to check monotonicity as on import
    values, dtype = _read_axis(group, axis)
    reverse = _is_decreasing(values, axis.name)
    values = values[::step]
    return (values[::-1] if reverse else values), dtype, reverse


def _set_image_coords(
    obj: ImageObj,
    xaxis: tuple[str | None, np.ndarray, np.dtype],
    yaxis: tuple[str | None, np.ndarray, np.dtype],
    conversions: list[str],
) -> None:
    """Set image coordinates: uniform if both axes are evenly spaced within
    :data:`UNIFORM_AXIS_TOLERANCE`, else the stored (non-uniform) coordinates

    Args:
        obj: image object
        xaxis: X axis name (None for a dimension without axis), values in
         increasing order, and their stored data type
        yaxis: Y axis name (None for a dimension without axis), values in
         increasing order, and their stored data type
        conversions: conversions applied to the source values, completed with the
         deviation of the axes converted to uniform coordinates
    """
    (xname, xc, xdtype), (yname, yc, ydtype) = xaxis, yaxis
    xdev, ydev = _uniform_deviation(xc, xdtype), _uniform_deviation(yc, ydtype)
    # Written so that a NaN deviation (non-finite axis values) is not uniform
    if not (xdev[1] <= UNIFORM_AXIS_TOLERANCE and ydev[1] <= UNIFORM_AXIS_TOLERANCE):
        obj.set_coords(xc, yc)
        return
    dx = float(xc[-1] - xc[0]) / (xc.size - 1) if xc.size > 1 else 1.0
    dy = float(yc[-1] - yc[0]) / (yc.size - 1) if yc.size > 1 else 1.0
    obj.set_uniform_coords(dx, dy, float(xc[0]), float(yc[0]))
    for name, dtype, (deviation, ulps) in (
        (xname, xdtype, xdev),
        (yname, ydtype, ydev),
    ):
        if name is not None and deviation > 0:
            ptype = np.dtype(_precision_type(dtype)).name
            conversions.append(
                f"axis '{name}': uniform coordinates "
                f"(max deviation {deviation:.3g}, {ulps:.2g} ULP of {ptype})"
            )


def _entry_group(group: h5py.Group) -> h5py.Group | None:
    """Return the ``NXentry`` group containing a group, if any"""
    while group.name != "/":
        group = group.parent
        if _text(group.attrs.get("NX_class", "")) == "NXentry":
            return group
    return None


def _entry_field(entry: h5py.Group, name: str) -> str:
    """Return a text field of an ``NXentry`` group (empty if missing)"""
    item = entry.get(name)
    if not isinstance(item, h5py.Dataset) or item.size != 1:
        return ""
    if item.dtype.kind not in "SUO":
        return ""
    return _text(item[()]).strip()


def entry_information(group: h5py.Group) -> tuple[dict[str, str], dict[str, str]]:
    """Return the title and the start and end times of the ``NXentry`` group
    containing a group, as ``experimental_source`` details and timestamps

    Args:
        group: HDF5 group

    Returns:
        Details (``{"entry_title": ...}``) and timestamps (``{"start": ...,
        "end": ...}``), without the missing fields
    """
    entry = _entry_group(group)
    if entry is None:
        return {}, {}
    title = _entry_field(entry, "title")
    details = {"entry_title": title} if title else {}
    timestamps = {
        key: value
        for key, value in (
            ("start", _entry_field(entry, "start_time")),
            ("end", _entry_field(entry, "end_time")),
        )
        if value
    }
    return details, timestamps


def default_nxdata_path(h5file: h5py.File) -> str | None:
    """Return the path of the default ``NXdata`` group of a NeXus file

    The ``@default`` attribute of the file designates its default entry, whose
    ``@default`` attribute designates its default ``NXdata`` group (or a subentry,
    designating its own).

    Args:
        h5file: HDF5 file

    Returns:
        Group path, or None if the file does not designate an ``NXdata`` group
    """
    group: h5py.Group = h5file
    path = "/"
    for _level in range(8):
        if "default" not in group.attrs:
            return None
        name = _text(group.attrs["default"]).strip()
        child = group.get(name)
        if not isinstance(child, h5py.Group):
            return None
        # Path in the file, also when the group is reached through an external
        # link (``child.name`` is then its path in its own file)
        path = "/" + (name if name.startswith("/") else f"{path}/{name}").strip("/")
        if _is_nxdata(child):
            return path
        group = child
    return None


class NXdataNode(common.GroupNode, NDViewMixin):
    """Node for NeXus ``NXdata`` groups, imported as a signal or an image, or
    through a view for signals of three dimensions or more

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
        self.init_view()

    @classmethod
    def match(cls, dset):
        """Return True if h5 group is an ``NXdata`` group with a numeric signal"""
        return describe_nxdata(dset) is not None

    @property
    def nd_shape(self) -> tuple[int, ...] | None:
        """Return the signal shape (None if the signal cannot be imported)"""
        return None if self.nxdata.problems else self.nxdata.shape

    @property
    def interpretation(self) -> str:
        """Return the ``interpretation`` attribute of the signal, or of the group
        (empty if not given)"""
        dset = self.dset.get(self.nxdata.signal)
        for item in (dset, self.dset):
            text = _text(item.attrs.get("interpretation", "")).strip()
            if text:
                return text
        return ""

    def is_supported(self) -> bool:
        """Return True if the signal is 1D or 2D and its axes are valid, or if the
        view of a multidimensional signal is enabled"""
        desc = self.nxdata
        if desc.problems:
            return False
        if len(desc.shape) >= 3:
            return self.import_view
        return int(np.prod(desc.shape)) > 1

    def can_preview(self) -> bool:
        """Return True if the signal is supported or can be viewed"""
        return self.view is not None or self.is_supported()

    @property
    def icon_name(self):
        """Icon name associated to node"""
        if len(self.nxdata.shape) >= 3 and self.import_view:
            return (
                "sigimax:image.svg"
                if len(self.view.displayed) == 2
                else "sigimax:signal.svg"
            )
        if self.is_supported():
            return (
                "sigimax:signal.svg"
                if len(self.nxdata.shape) == 1
                else "sigimax:image.svg"
            )
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

    def make_source(
        self, conversions: list[str], selection: NDSelection | None = None
    ) -> dict:
        """Return the experimental source of the imported object

        Dimensions without axis are recorded as ``"."``, as in NeXus ``@axes``. The
        title and times of the entry are recorded in the details and timestamps.

        Args:
            conversions: conversions applied to the source values
            selection: frame of a multidimensional signal (None: whole signal),
             recorded as ``view``, with the coordinates of the frame along the
             hidden axes as ``positions``
        """
        desc = self.nxdata
        chosen = {
            "signal": desc.signal,
            "axes": [axis.name if axis else "." for axis in desc.axes],
        }
        if selection is not None:
            chosen["view"] = selection.as_dict()
            positions = self.frame_positions(selection)
            if positions:
                chosen["positions"] = positions
        details, timestamps = entry_information(self.dset)
        details.update(self.source_details() or {})
        return make_experimental_source(
            self.SOURCE_KIND,
            self.h5file.filename,
            entry=self.h5path,
            selection=chosen,
            timestamps=timestamps or None,
            conversions=conversions or None,
            details=details or None,
        )

    def create_native_object(self):
        """Create signal or image object from the ``NXdata`` group"""
        if not self.is_supported() or len(self.nxdata.shape) >= 3:
            return None
        obj, conversions = self._build_object(1)
        set_experimental_source(obj, self.make_source(conversions))
        return obj

    def create_preview_object(self, max_items: int):
        """Return the native object, or a decimated one if the signal has more
        than ``max_items`` elements (only the read elements of its axes are kept);
        for multidimensional signals, the first frame of the view

        Args:
            max_items: maximum number of signal elements to read
        """
        if len(self.nxdata.shape) >= 3 and self.view is not None:
            return self.preview_view_object(max_items)
        if not self.is_supported():
            return None
        shape = self.nxdata.shape
        if math.prod(shape) <= max_items:
            return self.get_native_object()
        obj, _conversions = self._build_object(preview_step(shape, max_items))
        return obj

    def axis_name(self, dim: int) -> str:
        """Return the name of the axis of a dimension (empty if it has none)"""
        axis = self.nxdata.axes[dim]
        return "" if axis is None else axis.name

    def frame_positions(self, selection: NDSelection) -> dict[str, float]:
        """Return the coordinates of a frame along the hidden axes which have an
        axis, by axis name (bin centers for bin edges)"""
        positions = {}
        ndim = len(self.nxdata.shape)
        hidden = [dim for dim in range(ndim) if dim not in selection.displayed]
        for dim, index in zip(hidden, selection.indices):
            axis = self.nxdata.axes[dim]
            if axis is None:
                continue
            dset = self.dset[axis.name]
            values = np.asarray(dset[index : index + 2 if axis.edges else index + 1])
            positions[axis.name] = float(np.mean(values, dtype=float))
        return positions

    def create_view_object(
        self, selection: NDSelection, title: str, max_items: int | None = None
    ) -> SignalObj | ImageObj:
        """Create the signal or image of a frame of a multidimensional signal, with
        the axes of its displayed dimensions

        Args:
            selection: frame selection
            title: object title
            max_items: maximum number of elements to read (None: read the whole
             frame and record the origin of the object)
        """
        desc, group = self.nxdata, self.dset
        sizes = tuple(desc.shape[dim] for dim in selection.displayed)
        step = self.view_step(sizes, max_items)
        data = read_selection(group[desc.signal], selection, step)
        axes = tuple(desc.axes[dim] for dim in selection.displayed)
        conversions = [
            f"axis '{axis.name}': bin edges -> bin centers"
            for axis in axes
            if axis is not None and axis.edges
        ]
        if len(sizes) == 1:
            dy = None
            if desc.errors is not None:
                errors = read_selection(group[desc.errors], selection, step)
                dy = np.asarray(errors, dtype=float)
            obj = self._build_signal(data, step, axes[0], sizes[0], dy, title)
        else:
            obj = self._build_image(data, step, conversions, axes, sizes, title)
        if max_items is None:
            set_experimental_source(obj, self.make_source(conversions, selection))
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
            dy = None
            if desc.errors is not None:
                dy = np.asarray(self.dset[desc.errors][::step], dtype=float)
            obj = self._build_signal(data, step, desc.axes[0], desc.shape[0], dy)
            return obj, conversions
        obj = self._build_image(data, step, conversions, desc.axes, desc.shape)
        return obj, conversions

    def _build_signal(
        self,
        data: np.ndarray,
        step: int,
        axis: NXAxis | None,
        size: int,
        dy: np.ndarray | None = None,
        title: str | None = None,
    ) -> SignalObj:
        """Create a signal object from 1D values of the ``NXdata`` group

        Args:
            data: signal values, read with step
            step: step between the read elements
            axis: axis of the values (None: no axis)
            size: number of values along the dimension
            dy: uncertainties, read with step (None: no uncertainties)
            title: object title (default: node title)

        Returns:
            Signal object
        """
        desc, group = self.nxdata, self.dset
        x = np.arange(0, size, step, dtype=float)
        if axis is not None:
            x = _read_axis(group, axis, step)[0]
        y = common.to_signal_data(data)
        obj = create_signal(title or self.object_title, x, y, dy=dy)
        obj.ylabel, obj.yunit = desc.label, desc.units
        if axis is not None:
            obj.xlabel, obj.xunit = axis.label, axis.units
        return obj

    def _build_image(
        self,
        data: np.ndarray,
        step: int,
        conversions: list[str],
        axes: tuple[NXAxis | None, ...],
        sizes: tuple[int, ...],
        title: str | None = None,
    ) -> ImageObj:
        """Create an image object from 2D values of the ``NXdata`` group

        Args:
            data: image values, read with step along both dimensions
            step: step between the read elements
            conversions: conversions applied to the source values, completed with
             the ones applied to the image
            axes: axes of the rows and of the columns (None: no axis)
            sizes: number of rows and columns
            title: object title (default: node title)

        Returns:
            Image object
        """
        desc, group = self.nxdata, self.dset
        yaxis, xaxis = axes
        ny, nx = sizes
        # PlotPy images need increasing coordinates: decreasing axes are reversed
        xc, xdtype, xreversed = _image_axis(group, xaxis, nx, step)
        yc, ydtype, yreversed = _image_axis(group, yaxis, ny, step)
        for axis, reverse, dim in ((xaxis, xreversed, 1), (yaxis, yreversed, 0)):
            if reverse:
                data = np.flip(data, axis=dim)
                conversions.append(f"axis '{axis.name}': reversed to increasing order")
        obj = create_image(
            title or self.object_title,
            convert_array_to_valid_dtype(
                np.ascontiguousarray(data), ImageObj.VALID_DTYPES
            ),
        )
        obj.zlabel, obj.zunit = desc.label, desc.units
        _set_image_coords(
            obj,
            (xaxis.name if xaxis else None, xc, xdtype),
            (yaxis.name if yaxis else None, yc, ydtype),
            conversions,
        )
        if xaxis is not None:
            obj.xlabel, obj.xunit = xaxis.label, xaxis.units
        if yaxis is not None:
            obj.ylabel, obj.yunit = yaxis.label, yaxis.units
        if desc.errors is not None:
            conversions.append("uncertainties not imported (image)")
        return obj


class AuxiliarySignalNode(NXdataNode):
    """Node of an auxiliary signal of an ``NXdata`` group, imported with the axes
    that fit its dimensions

    Args:
        h5file: HDF5 file
        dname: path of the ``NXdata`` group
        nxdata: auxiliary signal description
    """

    def __init__(self, h5file, dname: str, nxdata: NXdataDescription):
        super().__init__(h5file, dname, nxdata)
        self.text_prefix = "NXdata auxiliary signal"

    @classmethod
    def match(cls, dset):
        """Auxiliary signal nodes are created with their group, not by HDF5 items"""
        return False

    @property
    def id(self):
        """Return node id, distinct from the HDF5 paths of the file"""
        return f"{self.h5path.rstrip('/')}::{self.nxdata.signal}"

    @property
    def name(self):
        """Return node name"""
        return self.nxdata.signal

    def collect_children(self, node_dict, ancestors=()):
        """Auxiliary signals have no children"""


def _auxiliary_children(node: common.GroupNode) -> list[AuxiliarySignalNode]:
    """Return the nodes of the auxiliary signals of an ``NXdata`` group node"""
    if type(node) is not NXdataNode:  # pylint: disable=unidiomatic-typecheck
        return []
    return [
        AuxiliarySignalNode(node.h5file, node.h5path, desc)
        for desc in describe_auxiliary_signals(node.dset, node.nxdata)
    ]


common.NODE_FACTORY.register(NXdataNode, is_generic=True)
common.NODE_FACTORY.add_children_provider(_auxiliary_children)
