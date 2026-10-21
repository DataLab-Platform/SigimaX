# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX HDF5 data mappings

Many files do not designate their plottable data with NeXus ``NXdata`` groups, or
designate it incompletely (no axes, several signals). A data mapping describes the
signals and images of such files declaratively: which groups it applies to, and
for each object, its signal dataset, the axis of each dimension, uncertainties,
labels and units. Mappings are JSON-compatible dictionaries, so that they can be
written, shared and versioned without code; no dataset path is coded in SigimaX.

A group matches a mapping when it has the expected attribute values and contains
the required paths. Each object of a matching group is shown in the HDF5 browser
as an extra node, imported like an ``NXdata`` group. Mapping layout (version 1)::

    {
        "version": 1,
        "name": "Counters versus time",
        "description": "Optional description",
        "match": {"attributes": {"NX_class": "NXdata"}, "paths": ["time_1"]},
        "objects": [
            {
                "name": "{name}",
                "signal": "data_*",
                "axes": [{"path": "time_1", "label": "Time", "units": "s"}],
                "errors": null,
                "label": null,
                "units": null
            }
        ]
    }

Paths are relative to the matching group. The last component of a signal path may
be a pattern (``*``, ``?``, ``[...]``): the object is then repeated for each
matching dataset, and ``{name}`` in its name is replaced by the dataset name.
``axes`` gives one entry per signal dimension (``null``: no axis), as a path or as
an object overriding the axis label and units; without ``axes``, dimensions have
no axis.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import json
import re
from typing import Any

import h5py
from sigima.objects import make_experimental_source

from sigimax.h5 import common, nexus

__all__ = [
    "MAPPING_VERSION",
    "DataMapping",
    "MappedAxis",
    "MappedDataNode",
    "MappedObject",
    "describe_mapping",
    "load_mapping",
    "mapping_from_dict",
    "register_mapping",
    "registered_mappings",
    "unregister_mapping",
]

#: Version of the data mapping layout
MAPPING_VERSION = 1

_PATTERN_CHARS = re.compile(r"[*?\[]")


@dataclasses.dataclass(frozen=True)
class MappedAxis:
    """Axis of a mapped signal dimension

    Args:
        path: axis dataset path, relative to the matching group
        label: axis label (default: ``long_name`` attribute, or dataset name)
        units: axis units (default: ``units`` attribute)
    """

    path: str
    label: str | None = None
    units: str | None = None


@dataclasses.dataclass(frozen=True)
class MappedObject:
    """Signal or image of a data mapping

    Args:
        name: object name, with ``{name}`` replaced by the dataset name when
         ``signal`` is a pattern
        signal: signal dataset path, relative to the matching group; its last
         component may be a pattern
        axes: axis of each signal dimension (None: no axis), or None if no
         dimension has an axis
        errors: uncertainties dataset path (default: ``<signal>_errors``, if any)
        label: signal label (default: ``long_name`` attribute, or dataset name)
        units: signal units (default: ``units`` attribute)
    """

    name: str
    signal: str
    axes: tuple[MappedAxis | None, ...] | None = None
    errors: str | None = None
    label: str | None = None
    units: str | None = None

    @property
    def is_pattern(self) -> bool:
        """Return True if the signal path ends with a pattern"""
        return bool(_PATTERN_CHARS.search(self.signal.rpartition("/")[2]))


@dataclasses.dataclass(frozen=True)
class DataMapping:
    """Declarative description of the signals and images of HDF5 groups

    Args:
        name: mapping name, shown in the HDF5 browser
        objects: mapped objects
        attributes: attribute values required on the matching groups
        paths: paths required in the matching groups
        description: mapping description
    """

    name: str
    objects: tuple[MappedObject, ...]
    attributes: dict[str, str] = dataclasses.field(default_factory=dict)
    paths: tuple[str, ...] = ()
    description: str = ""


def _check_keys(where: str, data: dict, allowed: set[str], required: set[str]):
    """Raise if data has unknown or missing keys"""
    if not isinstance(data, dict):
        raise ValueError(f"{where} must be an object")
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
    missing = required - set(data)
    if missing:
        raise ValueError(f"{where}: missing keys {sorted(missing)}")


def _text(where: str, value: Any, optional: bool = False) -> str | None:
    """Return value if it is a non-empty string, raise otherwise"""
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} must be a non-empty string")
    return value


def _path(where: str, value: Any, optional: bool = False) -> str | None:
    """Return value if it is a relative path, raise otherwise"""
    path = _text(where, value, optional)
    if path is not None and (path.startswith("/") or "" in path.split("/")):
        raise ValueError(f"{where} must be a relative path: {path!r}")
    return path


def _axis_from_data(where: str, data: Any) -> MappedAxis | None:
    """Return mapped axis from its JSON-compatible description"""
    if data is None:
        return None
    if isinstance(data, str):
        return MappedAxis(_path(where, data))
    _check_keys(where, data, {"path", "label", "units"}, {"path"})
    return MappedAxis(
        _path(f"{where}.path", data["path"]),
        _text(f"{where}.label", data.get("label"), optional=True),
        _text(f"{where}.units", data.get("units"), optional=True),
    )


def _object_from_data(where: str, data: Any) -> MappedObject:
    """Return mapped object from its JSON-compatible description"""
    keys = {"name", "signal", "axes", "errors", "label", "units"}
    _check_keys(where, data, keys, {"name", "signal"})
    axes = data.get("axes")
    if axes is not None:
        if not isinstance(axes, list):
            raise ValueError(f"{where}.axes must be a list")
        axes = tuple(
            _axis_from_data(f"{where}.axes[{index}]", axis)
            for index, axis in enumerate(axes)
        )
    obj = MappedObject(
        name=_text(f"{where}.name", data["name"]),
        signal=_path(f"{where}.signal", data["signal"]),
        axes=axes,
        errors=_path(f"{where}.errors", data.get("errors"), optional=True),
        label=_text(f"{where}.label", data.get("label"), optional=True),
        units=_text(f"{where}.units", data.get("units"), optional=True),
    )
    if "/" in obj.name:
        raise ValueError(f"{where}.name must not contain '/'")
    if obj.is_pattern and "{name}" not in obj.name:
        raise ValueError(f"{where}.name must contain '{{name}}' for a signal pattern")
    if _PATTERN_CHARS.search(obj.signal.rpartition("/")[0]):
        raise ValueError(f"{where}.signal: only its last component may be a pattern")
    return obj


def mapping_from_dict(data: dict[str, Any]) -> DataMapping:
    """Return a data mapping from its JSON-compatible description

    Args:
        data: mapping description (see module documentation)

    Returns:
        Data mapping

    Raises:
        ValueError: if the description is invalid
    """
    keys = {"version", "name", "description", "match", "objects"}
    _check_keys("mapping", data, keys, {"version", "name", "objects"})
    if data["version"] != MAPPING_VERSION:
        raise ValueError(f"Unsupported data mapping version: {data['version']!r}")
    match = data.get("match", {})
    _check_keys("mapping.match", match, {"attributes", "paths"}, set())
    attributes = match.get("attributes", {})
    if not isinstance(attributes, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in attributes.items()
    ):
        raise ValueError("mapping.match.attributes must map names to strings")
    paths = match.get("paths", [])
    if not isinstance(paths, list):
        raise ValueError("mapping.match.paths must be a list")
    objects = data["objects"]
    if not isinstance(objects, list) or not objects:
        raise ValueError("mapping.objects must be a non-empty list")
    mapping = DataMapping(
        name=_text("mapping.name", data["name"]),
        objects=tuple(
            _object_from_data(f"mapping.objects[{index}]", obj)
            for index, obj in enumerate(objects)
        ),
        attributes=dict(attributes),
        paths=tuple(
            _path(f"mapping.match.paths[{index}]", path)
            for index, path in enumerate(paths)
        ),
        description=data.get("description") or "",
    )
    if "/" in mapping.name:
        raise ValueError("mapping.name must not contain '/'")
    return mapping


def load_mapping(filename: str) -> DataMapping:
    """Load a data mapping from a JSON file

    Args:
        filename: JSON file name

    Returns:
        Data mapping

    Raises:
        ValueError: if the file is not a valid data mapping
    """
    try:
        with open(filename, encoding="utf-8") as fdesc:
            data = json.load(fdesc)
        return mapping_from_dict(data)
    except ValueError as exc:
        raise ValueError(f"Invalid data mapping '{filename}': {exc}") from exc


_MAPPINGS: dict[str, DataMapping] = {}


def register_mapping(mapping: DataMapping) -> None:
    """Register a data mapping, applied to the HDF5 files opened afterwards

    Args:
        mapping: data mapping

    Raises:
        ValueError: if another mapping with the same name is registered
    """
    registered = _MAPPINGS.get(mapping.name)
    if registered is not None and registered != mapping:
        raise ValueError(f"Another data mapping is named '{mapping.name}'")
    _MAPPINGS[mapping.name] = mapping


def unregister_mapping(name: str) -> None:
    """Unregister a data mapping, if registered

    Args:
        name: mapping name
    """
    _MAPPINGS.pop(name, None)


def registered_mappings() -> list[DataMapping]:
    """Return registered data mappings"""
    return list(_MAPPINGS.values())


def _matches(mapping: DataMapping, group: h5py.Group) -> bool:
    """Return True if group has the attributes and paths required by mapping"""
    for key, value in mapping.attributes.items():
        # pylint: disable-next=protected-access
        if key not in group.attrs or nexus._text(group.attrs[key]) != value:
            return False
    return all(group.get(path) is not None for path in mapping.paths)


def _natural_key(name: str) -> list:
    """Return sort key ordering numbered names numerically"""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


def _expand(obj: MappedObject, group: h5py.Group) -> list[tuple[str, str]]:
    """Return name and signal path of each object matching a mapped object"""
    if not obj.is_pattern:
        return [(obj.name, obj.signal)]
    parent, _sep, pattern = obj.signal.rpartition("/")
    container = group.get(parent) if parent else group
    if not isinstance(container, h5py.Group):
        return []
    excluded = {axis.path for axis in obj.axes or () if axis is not None}
    excluded.add(obj.errors)
    names = sorted(
        (name for name in container if fnmatch.fnmatchcase(name, pattern)),
        key=_natural_key,
    )
    items = []
    for name in names:
        path = f"{parent}/{name}" if parent else name
        if path not in excluded and not name.endswith("_errors"):
            items.append((obj.name.replace("{name}", name), path))
    return items


def _describe(
    obj: MappedObject, group: h5py.Group, signal: str
) -> nexus.NXdataDescription | None:
    """Return the description of a mapped signal"""
    dset = group.get(signal)
    if not isinstance(dset, h5py.Dataset):
        return None
    if obj.axes is None:
        axes: list[str | None] = [None] * dset.ndim
    else:
        axes = [None if axis is None else axis.path for axis in obj.axes]
    errors = (obj.errors,) if obj.errors else (f"{signal}_errors",)
    desc = nexus.describe_signal(group, signal, axes, errors=errors)
    if desc is None:
        return None
    problems = list(desc.problems)
    if obj.errors and desc.errors is None:
        problems.append(f"errors '{obj.errors}' do not match the signal shape")
    axis_descs = list(desc.axes)
    for index, axis in enumerate(obj.axes or ()):
        if index < len(axis_descs) and axis is not None and axis_descs[index]:
            axis_descs[index] = dataclasses.replace(
                axis_descs[index],
                label=axis.label or axis_descs[index].label,
                units=axis.units if axis.units is not None else axis_descs[index].units,
            )
    return dataclasses.replace(
        desc,
        axes=tuple(axis_descs),
        label=obj.label or desc.label,
        units=obj.units if obj.units is not None else desc.units,
        problems=tuple(problems),
    )


def describe_mapping(
    mapping: DataMapping, group: h5py.Group
) -> list[tuple[str, nexus.NXdataDescription]]:
    """Describe the objects of a group with a data mapping, without reading data

    Args:
        mapping: data mapping
        group: HDF5 group

    Returns:
        Name and description of each mapped object found in the group (empty if
        the group does not match the mapping)
    """
    if not isinstance(group, h5py.Group) or not _matches(mapping, group):
        return []
    items = []
    for obj in mapping.objects:
        for name, signal in _expand(obj, group):
            desc = _describe(obj, group, signal)
            if desc is not None:
                items.append((name, desc))
    return items


class MappedDataNode(nexus.NXdataNode):
    """Node of an object described by a data mapping

    Args:
        h5file: HDF5 file
        dname: path of the matching group
        mapping: data mapping
        name: object name
        nxdata: object description
    """

    def __init__(
        self,
        h5file,
        dname: str,
        mapping: DataMapping,
        name: str,
        nxdata: nexus.NXdataDescription,
    ):
        super().__init__(h5file, dname, nxdata)
        self.mapping = mapping
        self.object_name = name
        self.text_prefix = mapping.name

    @classmethod
    def match(cls, dset):
        """Mapped nodes are created by data mappings, not by HDF5 items"""
        return False

    @property
    def id(self):
        """Return node id, distinct from the HDF5 paths of the file"""
        return f"{self.dset.name.rstrip('/')}::{self.mapping.name}/{self.object_name}"

    @property
    def name(self):
        """Return node name"""
        return self.object_name

    def make_source(self, conversions: list[str]) -> dict:
        """Return the experimental source of the imported object"""
        desc = self.nxdata
        return make_experimental_source(
            "hdf5",
            self.h5file.filename,
            entry=desc.path,
            selection={
                "signal": desc.signal,
                "axes": [axis.name if axis else None for axis in desc.axes],
            },
            conversions=conversions or None,
            details={"mapping": self.mapping.name},
        )


def _mapped_children(node: common.GroupNode) -> list[MappedDataNode]:
    """Return the nodes of the mapped objects of a group node"""
    if not _MAPPINGS or not isinstance(node.dset, h5py.Group):
        return []
    return [
        MappedDataNode(node.h5file, node.dset.name, mapping, name, desc)
        for mapping in list(_MAPPINGS.values())
        for name, desc in describe_mapping(mapping, node.dset)
    ]


common.NODE_FACTORY.add_children_provider(_mapped_children)
