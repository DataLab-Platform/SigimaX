# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
NeXus ``NXdata`` unit tests
---------------------------

``NXdata`` groups are imported as signals or images with their axes, units and
uncertainties, following the NeXus conventions, and record their origin.
"""

from __future__ import annotations

import contextlib
import uuid
from typing import Callable

import h5py
import numpy as np
import pytest
import sigima.io
from sigima.objects import ImageObj, SignalObj, get_experimental_source

from sigimax.adapters_plotpy import create_adapter_from_object
from sigimax.h5 import H5Importer
from sigimax.h5.nexus import NXdataNode
from sigimax.h5.selection import preview_step

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


@contextlib.contextmanager
def _nodes_of(tmp_path, build: Callable[[h5py.File], None]):
    """Create a file with a builder function, and yield its nodes by path."""
    fname = str(tmp_path / f"{uuid.uuid4()}.nxs")
    with h5py.File(fname, "w") as h5file:
        build(h5file)
    importer = H5Importer(fname)
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


def test_nxdata_invalid_axes(tmp_path) -> None:
    """Axes that do not describe the signal dimensions, and axes or
    uncertainties that do not hold real numbers, are reported."""

    def build(h5file: h5py.File) -> None:
        short = _nxdata(h5file, "short", "data", ["x"])
        short["data"] = np.ones((3, 4))
        short["x"] = np.arange(4.0)
        long = _nxdata(h5file, "long", "data", ["y", "x", "z"])
        long["data"] = np.ones((3, 4))
        long["x"], long["y"], long["z"] = np.arange(4.0), np.arange(3.0), [0.0, 1.0]
        twice = _nxdata(h5file, "twice", "data", ["x", "y"])
        twice.attrs["x_indices"] = twice.attrs["y_indices"] = 0
        twice["data"] = np.ones((3, 4))
        twice["x"], twice["y"] = np.arange(3.0), np.arange(3.0)
        missing = _nxdata(h5file, "missing", "data", ["x"])
        missing.attrs["x_indices"] = 3
        missing["data"] = np.ones(4)
        missing["x"] = np.arange(4.0)
        spanning = _nxdata(h5file, "spanning", "data", ["x", "."])
        spanning.attrs["x_indices"] = [0, 1]
        spanning["data"] = np.ones((3, 4))
        spanning["x"] = np.arange(3.0)
        text = _nxdata(h5file, "text", "data", ["x"])
        text["data"] = np.ones(3)
        text["x"] = np.array([b"a", b"b", b"c"])
        text_errors = _nxdata(h5file, "text_errors", "data", ["x"])
        text_errors["data"] = np.ones(3)
        text_errors["x"] = np.arange(3.0)
        text_errors["data_errors"] = np.array([b"a", b"b", b"c"])

    with _nodes_of(tmp_path, build) as nodes:
        expected = {
            "short": "1 axes for 2 dimensions",
            "long": "3 axes for 2 dimensions",
            "twice": "axes 'x' and 'y' describe dimension 0",
            "missing": "axis 'x' refers to missing dimension 3",
            "spanning": "axis 'x' spans 2 dimensions",
            "text": "axis 'x' does not hold real numbers",
        }
        for name, problem in expected.items():
            node = nodes[f"/{name}"]
            assert not node.is_supported(), name
            assert problem in node.nxdata.problems, name
            assert problem in node.text, name
        node = nodes["/text_errors"]
        assert node.is_supported() and node.nxdata.errors is None
        assert isinstance(node.get_native_object(), SignalObj)


def _image_group(h5file: h5py.File, name: str, x, y=None) -> None:
    """Create an NXdata image group with an X axis, and optionally a Y axis."""
    ny = 2 if y is None else len(y)
    group = _nxdata(h5file, name, "data", ["." if y is None else "y", "x"])
    group["data"] = np.arange(ny * len(x), dtype=np.uint16).reshape(ny, len(x))
    group["x"] = x
    if y is not None:
        group["y"] = y


def test_nxdata_image_axes(tmp_path) -> None:
    """Uniform axes are detected within the precision of their data type, and
    decreasing axes are reversed (PlotPy images need increasing coordinates)."""

    def build(h5file: h5py.File) -> None:
        f32 = np.linspace(0.0, 1.0, 11, dtype=np.float32)
        _image_group(h5file, "float32", f32, f32)
        _image_group(h5file, "offset", np.linspace(1000.0, 1000.1, 1001))
        _image_group(h5file, "decreasing", [3.0, 2.0, 1.0, 0.0], [10.0, 5.0])
        _image_group(h5file, "decreasing_nu", [6.0, 3.0, 1.0, 0.0])
        _image_group(h5file, "constant", np.zeros(4))
        _image_group(h5file, "unordered", [0.0, 2.0, 1.0, 3.0])

    with _nodes_of(tmp_path, build) as nodes:
        image = nodes["/float32"].get_native_object()
        assert image.is_uniform_coords
        assert np.isclose(image.dx, 0.1) and np.isclose(image.dy, 0.1)

        image = nodes["/offset"].get_native_object()
        assert image.is_uniform_coords
        assert image.x0 == 1000.0
        assert np.isclose(image.dx, 1e-4, rtol=1e-12)

        image = nodes["/decreasing"].get_native_object()
        assert image.is_uniform_coords
        assert (image.x0, image.dx, image.y0, image.dy) == (0.0, 1.0, 5.0, 5.0)
        assert np.array_equal(image.data, np.arange(8).reshape(2, 4)[::-1, ::-1])
        assert get_experimental_source(image)["conversions"] == [
            "axis 'x': reversed to increasing order",
            "axis 'y': reversed to increasing order",
        ]
        create_adapter_from_object(image).make_item()

        image = nodes["/decreasing_nu"].get_native_object()
        assert not image.is_uniform_coords
        assert np.array_equal(image.xcoords, [0.0, 1.0, 3.0, 6.0])
        assert np.array_equal(image.data, np.arange(8).reshape(2, 4)[:, ::-1])
        create_adapter_from_object(image).make_item()

        for name in ("constant", "unordered"):
            with pytest.raises(ValueError, match="not strictly monotonic"):
                nodes[f"/{name}"].get_native_object()


def test_nxdata_decimated_preview(tmp_path) -> None:
    """Previews of large NXdata groups read one element out of a step, with the
    matching axis values; small groups are previewed with the native object."""

    def build(h5file: h5py.File) -> None:
        image = _nxdata(h5file, "image", "data", ["y", "x"])
        image["data"] = np.arange(300 * 400, dtype=np.float32).reshape(300, 400)
        image["x"] = np.linspace(0.0, 39.9, 400)
        image["y"] = np.linspace(29.9, 0.0, 300)  # Decreasing: reversed
        spectrum = _nxdata(h5file, "spectrum", "counts", "energy")
        spectrum["counts"] = np.arange(5000.0)
        spectrum["counts_errors"] = np.full(5000, 0.5)
        spectrum["energy"] = np.linspace(8.0, 9.0, 5001)  # Bin edges

    with _nodes_of(tmp_path, build) as nodes:
        preview = nodes["/image"].create_preview_object(1000)
        step = preview_step((300, 400), 1000)
        assert preview.data.shape == (25, 34) and preview.data.size <= 1000
        assert preview.is_uniform_coords
        assert np.isclose(preview.dx, 0.1 * step) and preview.x0 == 0.0
        # Rows 0, step... 24 * step are read, then reversed with the Y axis
        assert np.isclose(preview.y0, 29.9 - 24 * step * 0.1)
        assert np.isclose(preview.dy, 0.1 * step)
        assert preview.data[0, 0] == 24 * step * 400
        assert preview.data[-1, 1] == step

        node = nodes["/spectrum"]
        preview = node.create_preview_object(1000)
        native = node.get_native_object()
        assert preview.y.size <= 1000
        step = preview_step((5000,), 1000)
        assert np.allclose(preview.x, native.x[::step])
        assert np.array_equal(preview.y, native.y[::step])
        assert np.array_equal(preview.dy, native.dy[::step])
        assert node.create_preview_object(5000) is native


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
