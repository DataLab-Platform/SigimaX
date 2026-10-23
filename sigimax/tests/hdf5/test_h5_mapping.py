# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 data mapping unit tests
----------------------------

Declarative data mappings describe the signals and images of groups that do not
designate them with NeXus ``NXdata`` groups: they are validated when loaded, apply
only to matching groups, and their objects are imported with their axes, labels,
units and origin.
"""

from __future__ import annotations

import json
import uuid

import h5py
import numpy as np
import pytest
from sigima.objects import ImageObj, SignalObj, get_experimental_source

from sigimax.h5 import H5Importer
from sigimax.h5.mapping import (
    MappedDataNode,
    describe_mapping,
    load_mapping,
    mapping_from_dict,
    register_mapping,
    registered_mappings,
    unregister_mapping,
)

pytestmark = pytest.mark.unit

COUNTERS = {
    "version": 1,
    "name": "Counters",
    "match": {"attributes": {"NX_class": "NXdata"}, "paths": ["time_1"]},
    "objects": [
        {
            "name": "{name}",
            "signal": "data_*",
            "axes": [{"path": "time_1", "label": "Elapsed time"}],
        }
    ],
}

MEASUREMENT = {
    "version": 1,
    "name": "Measurement",
    "match": {"attributes": {"NX_class": "NXentry"}, "paths": ["measurement"]},
    "objects": [
        {
            "name": "Transmission",
            "signal": "measurement/it",
            "axes": ["measurement/energy"],
            "units": "counts",
        },
        {
            "name": "Map",
            "signal": "measurement/map",
            "axes": ["measurement/y", {"path": "measurement/x", "units": "mm"}],
        },
        {
            "name": "Columns",
            "signal": "measurement/map",
            "axes": [None, "measurement/x"],
        },
        {"name": "Missing", "signal": "measurement/absent"},
        {
            "name": "Bad errors",
            "signal": "measurement/it",
            "axes": ["measurement/energy"],
            "errors": "measurement/map",
        },
    ],
}


@pytest.fixture(name="h5fname")
def fixture_h5fname(tmp_path) -> str:
    """HDF5 file with scan counters and a measurement group without NXdata axes"""
    fname = str(tmp_path / f"{uuid.uuid4()}.nxs")
    with h5py.File(fname, "w") as h5file:
        entry = h5file.create_group("entry")
        entry.attrs["NX_class"] = "NXentry"
        scan = entry.create_group("scan_data")
        scan.attrs["NX_class"] = b"NXdata"
        for index in (1, 2, 10):
            scan[f"data_{index}"] = np.arange(4, dtype=float) * index
            scan[f"data_{index}"].attrs["signal"] = index
            scan[f"data_{index}"].attrs["units"] = b" "
        scan["data_2_errors"] = np.full(4, 0.5)
        # Latin-1 units, as variable-length and fixed-length strings
        scan["data_2"].attrs["units"] = b"\xb5m"
        scan["data_10"].attrs["units"] = np.bytes_(b"\xb5m")
        scan["time_1"] = np.array([0.0, 0.5, 1.0, 1.5])
        scan["time_1"].attrs["units"] = "s"
        measurement = entry.create_group("measurement")
        measurement["energy"] = np.array([8970.0, 8980.0, 8990.0])
        measurement["energy"].attrs["units"] = "eV"
        measurement["it"] = np.array([10, 7, 4], dtype=np.int32)
        measurement["it"].attrs["units"] = b" "
        measurement["map"] = np.arange(6, dtype=np.uint16).reshape(2, 3)
        measurement["x"] = np.array([0.0, 1.0, 2.0])
        measurement["y"] = np.array([5.0, 7.0])
        other = h5file.create_group("other")
        other.attrs["NX_class"] = "NXdata"
        other["data_1"] = np.ones(3)
    return fname


@pytest.fixture(name="mappings")
def fixture_mappings():
    """Register the test mappings, and unregister them afterwards"""
    mappings = [mapping_from_dict(COUNTERS), mapping_from_dict(MEASUREMENT)]
    for mapping in mappings:
        register_mapping(mapping)
    yield mappings
    for mapping in mappings:
        unregister_mapping(mapping.name)


def _mapped_nodes(importer: H5Importer) -> dict[str, MappedDataNode]:
    """Return mapped nodes of an importer, by name"""
    return {
        node.name: node for node in importer.nodes if isinstance(node, MappedDataNode)
    }


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"version": 2}, "Unsupported data mapping version"),
        ({"extra": 1}, "unknown keys"),
        ({"name": "a/b"}, "must not contain '/'"),
        ({"objects": []}, "non-empty list"),
        ({"match": {"paths": ["/abs"]}}, "relative path"),
        ({"match": {"attributes": {"NX_class": 1}}}, "map names to strings"),
        ({"objects": [{"name": "x", "signal": "data_*"}]}, "'{name}'"),
        ({"objects": [{"name": "{name}", "signal": "d*/x"}]}, "last component"),
        ({"objects": [{"name": "x", "signal": "s", "axes": "t"}]}, "must be a list"),
        ({"objects": [{"name": "x"}]}, "missing keys"),
    ],
    ids=lambda value: str(value)[:30],
)
def test_invalid_mapping(change: dict, message: str) -> None:
    """Invalid descriptions are rejected with an explicit reason"""
    with pytest.raises(ValueError, match=message):
        mapping_from_dict({**COUNTERS, **change})


def test_load_mapping(tmp_path) -> None:
    """Mappings are loaded from JSON files, whose name is given on error"""
    good = tmp_path / "good.json"
    good.write_text(json.dumps(COUNTERS), encoding="utf-8")
    assert load_mapping(str(good)) == mapping_from_dict(COUNTERS)
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="bad.json"):
        load_mapping(str(bad))


def test_register_mapping() -> None:
    """A name designates one mapping; registering it again is harmless"""
    mapping = mapping_from_dict(COUNTERS)
    register_mapping(mapping)
    try:
        register_mapping(mapping_from_dict(COUNTERS))
        other = mapping_from_dict({**COUNTERS, "description": "other"})
        with pytest.raises(ValueError, match="Another data mapping"):
            register_mapping(other)
        assert registered_mappings().count(mapping) == 1
    finally:
        unregister_mapping(mapping.name)
    assert mapping not in registered_mappings()


def test_describe_mapping(h5fname: str) -> None:
    """Only matching groups are described; patterns follow numeric order"""
    counters = mapping_from_dict(COUNTERS)
    with h5py.File(h5fname, "r") as h5file:
        items = describe_mapping(counters, h5file["entry/scan_data"])
        assert [name for name, _desc in items] == ["data_1", "data_2", "data_10"]
        desc = dict(items)["data_2"]
        assert desc.errors == "data_2_errors"
        assert desc.units == dict(items)["data_10"].units == "\u00b5m"
        assert desc.axes[0].label == "Elapsed time" and desc.axes[0].units == "s"
        assert not describe_mapping(counters, h5file["other"])
        assert not describe_mapping(counters, h5file["entry"])


@pytest.mark.usefixtures("mappings")
def test_mapped_nodes(h5fname: str) -> None:
    """Mapped objects are imported with their axes, labels, units and origin"""
    importer = H5Importer(h5fname)
    try:
        nodes = _mapped_nodes(importer)
        expected = {
            "data_1",
            "data_2",
            "data_10",
            "Transmission",
            "Map",
            "Columns",
            "Bad errors",
        }
        assert set(nodes) == expected
        assert not nodes["Bad errors"].is_supported()
        assert "is not a numeric dataset with the signal shape" in (
            nodes["Bad errors"].text
        )
        node = nodes["data_10"]
        assert node.id == "/entry/scan_data::Counters/data_10"
        assert importer.get(node.id) is node
        assert node in importer.get("/entry/scan_data").children

        signal = nodes["data_2"].get_native_object()
        assert isinstance(signal, SignalObj)
        np.testing.assert_array_equal(signal.x, [0.0, 0.5, 1.0, 1.5])
        np.testing.assert_array_equal(signal.y, [0.0, 2.0, 4.0, 6.0])
        np.testing.assert_array_equal(signal.dy, np.full(4, 0.5))
        assert (signal.xlabel, signal.xunit) == ("Elapsed time", "s")
        assert nodes["data_1"].get_native_object().yunit == ""
        source = get_experimental_source(signal)
        assert source["kind"] == "hdf5" and source["entry"] == "/entry/scan_data"
        assert source["selection"] == {"signal": "data_2", "axes": ["time_1"]}
        assert source["details"] == {"mapping": "Counters"}

        transmission = nodes["Transmission"].get_native_object()
        np.testing.assert_array_equal(transmission.x, [8970.0, 8980.0, 8990.0])
        assert (transmission.ylabel, transmission.yunit) == ("it", "counts")
        assert (transmission.xlabel, transmission.xunit) == ("energy", "eV")

        image = nodes["Map"].get_native_object()
        assert isinstance(image, ImageObj)
        assert (image.x0, image.y0, image.dx, image.dy) == (0.0, 5.0, 1.0, 2.0)
        assert (image.xunit, image.ylabel) == ("mm", "y")

        # Dimensions without axis are recorded as '.', as in NeXus files
        columns = nodes["Columns"].get_native_object()
        assert get_experimental_source(columns)["selection"] == {
            "signal": "measurement/map",
            "axes": [".", "measurement/x"],
        }
    finally:
        importer.close()


def test_mapping_problems(h5fname: str) -> None:
    """Objects that cannot be imported as described are shown with the reason"""
    mapping = mapping_from_dict(MEASUREMENT)
    with h5py.File(h5fname, "r") as h5file:
        items = dict(describe_mapping(mapping, h5file["entry"]))
    assert "Missing" not in items
    assert items["Bad errors"].problems == (
        "errors 'measurement/map' is not a numeric dataset with the signal shape",
    )


def test_unregistered_mapping(h5fname: str) -> None:
    """Files are browsed without mapped nodes when no mapping is registered"""
    importer = H5Importer(h5fname)
    try:
        assert not _mapped_nodes(importer)
    finally:
        importer.close()
