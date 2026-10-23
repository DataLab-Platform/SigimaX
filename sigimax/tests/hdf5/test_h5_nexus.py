# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
NeXus ``NXdata`` unit tests
---------------------------

``NXdata`` groups are imported as signals or images with their axes, units and
uncertainties, following the NeXus conventions, and record their origin.
"""

from __future__ import annotations

import uuid

import h5py
import numpy as np
import pytest
import sigima.io
from sigima.objects import ImageObj, SignalObj, get_experimental_source

from sigimax.h5 import H5Importer
from sigimax.h5.nexus import NXdataNode

pytestmark = pytest.mark.unit


def _nxdata(parent: h5py.Group, name: str, signal: str, axes) -> h5py.Group:
    """Create an NXdata group"""
    group = parent.create_group(name)
    group.attrs["NX_class"] = "NXdata"
    group.attrs["signal"] = signal
    if axes is not None:
        group.attrs["axes"] = axes
    return group


@pytest.fixture(name="nxsfname")
def fixture_nxsfname(tmp_path) -> str:
    """NeXus file covering the supported NXdata conventions."""
    fname = str(tmp_path / f"{uuid.uuid4()}.nxs")
    with h5py.File(fname, "w") as h5file:
        entry = h5file.create_group("entry")
        entry.attrs["NX_class"] = "NXentry"

        spectrum = _nxdata(entry, "spectrum", "counts", "energy")
        spectrum["counts"] = np.array([5, 9, 30, 8], dtype=np.uint32)
        spectrum["counts"].attrs["units"] = "counts"
        spectrum["counts"].attrs["long_name"] = "Intensity"
        spectrum["counts_errors"] = np.sqrt([5.0, 9.0, 30.0, 8.0])
        spectrum["energy"] = np.array([8.0, 8.1, 8.25, 8.5])
        spectrum["energy"].attrs["units"] = "keV"

        histogram = _nxdata(entry, "histogram", "hits", ["tof"])
        histogram["hits"] = np.array([1.0, 4.0, 2.0])
        histogram["tof"] = np.array([0.0, 2.0, 4.0, 8.0])

        image = _nxdata(entry, "map", "intensity", np.array([b"y", b"x"]))
        image["intensity"] = np.arange(12, dtype=np.uint16).reshape(3, 4)
        image["x"] = np.array([0.0, 1.0, 3.0, 6.0])
        image["x"].attrs["units"] = "mm"
        image["y"] = np.array([10.0, 20.0, 30.0])

        indexed = _nxdata(entry, "indexed", "data", np.array([b"x", b"y"]))
        indexed.attrs["x_indices"] = 1
        indexed.attrs["y_indices"] = 0
        indexed["data"] = np.ones((2, 3))
        indexed["x"] = np.array([0.5, 1.0, 1.5])
        indexed["y"] = np.array([-1.0, 1.0])

        partial = _nxdata(entry, "partial", "data", np.array([b".", b"x"]))
        partial["data"] = np.ones((2, 3))
        partial["x"] = np.array([0.0, 2.0, 4.0])

        legacy = entry.create_group("legacy")
        legacy.attrs["NX_class"] = b"NXdata"
        legacy["y"] = np.array([1.0, 2.0, 3.0])
        legacy["y"].attrs["signal"] = 1
        legacy["y"].attrs["axes"] = "t"
        legacy["t"] = np.array([0.0, 0.1, 0.2])

        broken = _nxdata(entry, "broken", "counts", "energy")
        broken["counts"] = np.ones(4)
        broken["energy"] = np.ones(7)

        stack = _nxdata(entry, "stack", "frames", np.array([b".", b"y", b"x"]))
        stack["frames"] = np.zeros((5, 3, 4))
        stack["x"] = np.arange(4.0)
        stack["y"] = np.arange(3.0)

        plain = entry.create_group("plain")
        plain["data"] = np.ones(3)
    return fname


@pytest.fixture(name="nodes")
def fixture_nodes(nxsfname: str):
    """Nodes of the NeXus file, by path."""
    importer = H5Importer(nxsfname)
    try:
        yield {node.id: node for node in importer.nodes}
    finally:
        importer.close()


def test_nxdata_classification(nodes: dict) -> None:
    """NXdata groups are recognized; invalid ones are shown but not importable."""
    for name in ("spectrum", "histogram", "map", "indexed", "legacy"):
        node = nodes[f"/entry/{name}"]
        assert isinstance(node, NXdataNode) and node.is_supported(), name
    assert not isinstance(nodes["/entry/plain"], NXdataNode)
    assert not isinstance(nodes["/entry"], NXdataNode)
    broken = nodes["/entry/broken"]
    assert not broken.is_supported()
    assert "axis 'energy' has 7 values for 4 points" in broken.text
    stack = nodes["/entry/stack"]
    assert not stack.is_supported()
    assert stack.shape_str == "5 x 3 x 4"
    assert nodes["/entry/spectrum"].icon_name == "signal.svg"
    assert nodes["/entry/map"].icon_name == "image.svg"
    # Datasets of NXdata groups remain available as raw nodes
    assert nodes["/entry/spectrum/counts"].is_supported()


def test_nxdata_signal(nodes: dict, nxsfname: str) -> None:
    """1D NXdata: axis values, units, labels, uncertainties and origin."""
    obj = nodes["/entry/spectrum"].get_native_object()
    assert isinstance(obj, SignalObj)
    assert np.array_equal(obj.x, [8.0, 8.1, 8.25, 8.5])
    assert np.array_equal(obj.y, [5.0, 9.0, 30.0, 8.0])
    assert np.allclose(obj.dy, np.sqrt([5.0, 9.0, 30.0, 8.0]))
    assert (obj.xlabel, obj.xunit) == ("energy", "keV")
    assert (obj.ylabel, obj.yunit) == ("Intensity", "counts")
    assert get_experimental_source(obj) == {
        "version": 1,
        "kind": "nexus",
        "location": nxsfname,
        "entry": "/entry/spectrum",
        "selection": {"signal": "counts", "axes": ["energy"]},
    }
    legacy = nodes["/entry/legacy"].get_native_object()
    assert np.array_equal(legacy.x, [0.0, 0.1, 0.2])
    assert np.array_equal(legacy.y, [1.0, 2.0, 3.0])


def test_nxdata_bin_edges(nodes: dict) -> None:
    """Bin edges are converted to bin centers, and the conversion is recorded."""
    obj = nodes["/entry/histogram"].get_native_object()
    assert np.array_equal(obj.x, [1.0, 3.0, 6.0])
    source = get_experimental_source(obj)
    assert source["conversions"] == ["axis 'tof': bin edges -> bin centers"]


def test_nxdata_image(nodes: dict) -> None:
    """2D NXdata: rows follow the first axis, non-uniform axes are kept."""
    obj = nodes["/entry/map"].get_native_object()
    assert isinstance(obj, ImageObj)
    assert obj.data.dtype == np.uint16
    assert np.array_equal(obj.data, np.arange(12).reshape(3, 4))
    assert not obj.is_uniform_coords
    assert np.array_equal(obj.xcoords, [0.0, 1.0, 3.0, 6.0])
    assert np.array_equal(obj.ycoords, [10.0, 20.0, 30.0])
    assert obj.xunit == "mm"
    indexed = nodes["/entry/indexed"].get_native_object()
    assert indexed.is_uniform_coords
    assert (indexed.x0, indexed.dx, indexed.y0, indexed.dy) == (0.5, 0.5, -1.0, 2.0)


def test_nxdata_missing_axis_source(nodes: dict, tmp_path) -> None:
    """Dimensions without axis are recorded as '.', which files restore."""
    obj = nodes["/entry/partial"].get_native_object()
    source = get_experimental_source(obj)
    assert source["selection"] == {"signal": "data", "axes": [".", "x"]}
    fname = str(tmp_path / "partial.h5ima")
    sigima.io.write_image(fname, obj)
    assert get_experimental_source(sigima.io.read_image(fname)) == source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
