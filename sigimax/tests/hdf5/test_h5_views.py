# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Multidimensional views and NeXus conventions unit tests
--------------------------------------------------------

Datasets of three dimensions or more are imported through a view, one signal or
image per frame. Legacy NeXus ``axis``/``primary`` attributes designate axes by
dimension, auxiliary signals are shown as nodes of their own, entries give the
title and times recorded in the origin, ``@default`` designates the default
``NXdata`` group, and signals compressed with unavailable filters are reported.
"""

from __future__ import annotations

import contextlib
import uuid
from typing import Callable

import h5py
import hdf5plugin
import numpy as np
import pytest
from sigima.objects import ImageObj, SignalObj, get_experimental_source

from sigimax.h5 import H5Importer
from sigimax.h5.generic import GenericNDArrayNode
from sigimax.h5.mapping import (
    describe_mapping,
    mapping_from_dict,
)
from sigimax.h5.nexus import (
    AuxiliarySignalNode,
    NXdataNode,
    default_nxdata_path,
    entry_information,
)
from sigimax.h5.selection import NDSelection, NDView, default_view
from sigimax.h5.views import FrameNode, count_frames, expand_views

pytestmark = pytest.mark.unit


@contextlib.contextmanager
def _nodes_of(tmp_path, build: Callable[[h5py.File], None]):
    """Create a file with a builder function, and yield its nodes by id."""
    fname = str(tmp_path / f"{uuid.uuid4()}.nxs")
    with h5py.File(fname, "w") as h5file:
        build(h5file)
    importer = H5Importer(fname)
    try:
        yield {node.id: node for node in importer.nodes}
    finally:
        importer.close()


def test_view_frames() -> None:
    """Views give one selection per frame, and are validated."""
    view = NDView((1, 2), (1,), 0, 5, 2)
    assert view.hidden_axes(3) == [0]
    assert list(view.frame_indices(3)) == [1, 3, 5]
    assert view.selections((6, 4, 5)) == [
        NDSelection((1, 2), (index,)) for index in (1, 3, 5)
    ]
    assert view.as_dict() == {
        "displayed": [1, 2],
        "indices": [1],
        "frame_axis": 0,
        "last": 5,
        "step": 2,
    }
    spectra = NDView((2,), (0, 3), 0, 1)
    assert spectra.selections((2, 4, 8)) == [
        NDSelection((2,), (0, 3)),
        NDSelection((2,), (1, 3)),
    ]
    for invalid, message in (
        (NDView((1, 2), (0,), 0, 6), "Last frame 6 out of range"),
        (NDView((1, 2), (0,), 1, 0), "is displayed or missing"),
        (NDView((1, 2), (0,), 0, 1, 0), "must be positive"),
    ):
        with pytest.raises(ValueError, match=message):
            invalid.validate((6, 4, 5))


def test_first_selection() -> None:
    """The first frame of a view is selected without building the selections of
    the other frames, even for a huge number of frames."""
    view = NDView((1, 2), (1,), 0, 5, 2)
    assert view.first_selection((6, 4, 5)) == view.selections((6, 4, 5))[0]
    huge = NDView((1, 2), (3,), 0, 10**9 - 1)
    assert huge.first_selection((10**9, 4, 5)) == NDSelection((1, 2), (3,))
    with pytest.raises(ValueError, match="Last frame 6 out of range"):
        NDView((1, 2), (0,), 0, 6).first_selection((6, 4, 5))


def test_default_views() -> None:
    """Default views follow the NeXus interpretation of the data."""
    assert default_view((5, 3, 4)) == NDView((1, 2), (0,), 0, 4)
    assert default_view((2, 5, 3, 4)) == NDView((2, 3), (0, 0), 1, 4)
    assert default_view((5, 8), "spectrum") == NDView((1,), (0,), 0, 4)
    assert default_view((6, 4, 3), "rgba-image") == NDView((0, 1), (0,), 2, 2)
    with pytest.raises(ValueError, match="two dimensions or more"):
        default_view((5,))


def test_interpretation(tmp_path) -> None:
    """The interpretation of a signal is read on its dataset or on its group."""

    def build(h5file: h5py.File) -> None:
        rgb = h5file.create_group("rgb")
        rgb.attrs.update(NX_class="NXdata", signal="img", interpretation="rgba-image")
        rgb["img"] = np.zeros((6, 4, 3), dtype=np.uint8)
        spectra = h5file.create_group("spectra")
        spectra.attrs.update(NX_class="NXdata", signal="counts")
        spectra["counts"] = np.zeros((2, 3, 16))
        spectra["counts"].attrs["interpretation"] = "spectrum"

    with _nodes_of(tmp_path, build) as nodes:
        assert nodes["/rgb"].view == NDView((0, 1), (0,), 2, 2)
        assert nodes["/spectra"].view == NDView((2,), (0, 0), 1, 2)


def _step_scan(h5file: h5py.File) -> None:
    """Scan written as by SOLEIL: legacy attributes, counters and detectors of
    several ranks all designated as signals, time stamps with axis 0"""
    entry = h5file.create_group("scan_0494")
    entry.attrs["NX_class"] = "NXentry"
    entry["title"] = np.array([b"step scan"])
    entry["start_time"] = "2021-03-16T15:06:05+01:00"
    scan = entry.create_group("scan_data")
    scan.attrs["NX_class"] = "NXdata"
    scan["actuator_1_1"] = np.array([10.0, 10.5, 11.0])
    scan["actuator_1_1"].attrs.update(axis=np.int32(1), primary=np.int32(1))
    scan["actuator_1_1"].attrs["units"] = "deg"
    scan["trajectory_1_1"] = np.array([10.0, 10.5, 11.0])
    scan["trajectory_1_1"].attrs.update(axis=np.int32(1), primary=np.int32(2))
    scan["sensors_rel_timestamps"] = np.array([0.0, 1.0, 2.0])
    scan["sensors_rel_timestamps"].attrs["axis"] = np.int32(0)
    scan["data_01"] = np.array([1.0, 2.0, 3.0])
    scan["data_02"] = np.arange(3 * 8, dtype=np.int32).reshape(3, 8)
    scan["data_03"] = np.arange(3 * 4 * 5, dtype=np.uint16).reshape(3, 4, 5)
    scan["data_03"].attrs["interpretation"] = "image"
    for name in ("data_01", "data_02", "data_03"):
        scan[name].attrs["signal"] = np.int32(1)


def test_legacy_axes_and_auxiliary_signals(tmp_path) -> None:
    """Legacy axis attributes give the axis of each dimension that fits, the
    primary one first; other signals are auxiliary signal nodes."""
    with _nodes_of(tmp_path, _step_scan) as nodes:
        main = nodes["/scan_0494/scan_data"]
        assert main.__class__ is NXdataNode and main.is_supported()
        assert main.text == "NXdata: data_01 (actuator_1_1)"
        signal = main.get_native_object()
        assert isinstance(signal, SignalObj)
        np.testing.assert_array_equal(signal.x, [10.0, 10.5, 11.0])
        assert (signal.xlabel, signal.xunit) == ("actuator_1_1", "deg")
        source = get_experimental_source(signal)
        assert source["details"] == {"entry_title": "step scan"}
        assert source["timestamps"] == {"start": "2021-03-16T15:06:05+01:00"}
        image = nodes["/scan_0494/scan_data::data_02"]
        assert isinstance(image, AuxiliarySignalNode) and image.is_supported()
        assert image.text == "NXdata auxiliary signal: data_02 (actuator_1_1, .)"
        obj = image.get_native_object()
        assert isinstance(obj, ImageObj) and obj.data.shape == (3, 8)
        assert (obj.y0, obj.dy, obj.ylabel) == (10.0, 0.5, "actuator_1_1")
        assert get_experimental_source(obj)["selection"]["signal"] == "data_02"
        stack = nodes["/scan_0494/scan_data::data_03"]
        assert not stack.is_supported() and stack.can_preview()
        assert stack.view == NDView((1, 2), (0,), 0, 2)


def test_auxiliary_signals_attribute(tmp_path) -> None:
    """Auxiliary signals of the @auxiliary_signals attribute have the signal
    axes."""

    def build(h5file: h5py.File) -> None:
        group = h5file.create_group("data")
        group.attrs.update(NX_class="NXdata", signal="I", axes=["energy"])
        group.attrs["auxiliary_signals"] = ["I0", "missing"]
        group["energy"] = np.array([1.0, 2.0, 4.0])
        group["I"] = np.ones(3)
        group["I0"] = np.full(3, 2.0)

    with _nodes_of(tmp_path, build) as nodes:
        signal = nodes["/data::I0"].get_native_object()
        np.testing.assert_array_equal(signal.x, [1.0, 2.0, 4.0])
        np.testing.assert_array_equal(signal.y, [2.0, 2.0, 2.0])
        assert "/data::missing" not in nodes


def test_nxdata_frames(tmp_path) -> None:
    """Frames of a multidimensional NXdata signal are images with the axes of the
    displayed dimensions, titled and located with the frame axis values."""

    def build(h5file: h5py.File) -> None:
        group = h5file.create_group("stack")
        group.attrs.update(NX_class="NXdata", signal="frames")
        group.attrs["axes"] = np.array([b"theta", b".", b"x"])
        group["frames"] = np.arange(4 * 3 * 2, dtype=np.uint16).reshape(4, 3, 2)
        group["theta"] = np.array([0.0, 0.1, 0.2, 0.3])
        group["x"] = np.array([5.0, 7.0])

    with _nodes_of(tmp_path, build) as nodes:
        node = nodes["/stack"]
        assert not node.is_supported() and node.create_native_object() is None
        assert not expand_views([node]) and count_frames([node]) == 0
        node.set_view(NDView((1, 2), (1,), 0, 3, 2))
        assert node.is_supported() and node.frame_count() == 2
        frames = expand_views([node])
        assert count_frames([node]) == len(frames)
        assert all(isinstance(frame, FrameNode) for frame in frames)
        first, second = (frame.get_native_object() for frame in frames)
        assert first.title.startswith("stack[1, :, :] (theta=0.1)")
        np.testing.assert_array_equal(first.data, np.arange(6, 12).reshape(3, 2))
        assert (first.x0, first.dx, first.xlabel) == (5.0, 2.0, "x")
        np.testing.assert_array_equal(second.data, np.arange(18, 24).reshape(3, 2))
        source = get_experimental_source(second)
        assert source["selection"]["view"] == {"displayed": [1, 2], "indices": [3]}
        assert source["selection"]["positions"] == {"theta": 0.3}
        node.set_view(NDView((0,), (0, 1), 1, 2))
        spectrum = expand_views([node])[1].get_native_object()
        np.testing.assert_array_equal(spectrum.x, [0.0, 0.1, 0.2, 0.3])
        np.testing.assert_array_equal(spectrum.y, [3, 9, 15, 21])
        preview = node.create_preview_object(2)
        assert isinstance(preview, SignalObj) and preview.y.size == 2
        assert get_experimental_source(preview) is None


def test_generic_frames(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Frames of a plain dataset have pixel coordinates; the preview reads the
    first frame without building the selections of the others."""

    def build(h5file: h5py.File) -> None:
        h5file["cube"] = np.arange(2 * 3 * 4, dtype=float).reshape(2, 3, 4)

    with _nodes_of(tmp_path, build) as nodes:
        node = nodes["/cube"]
        assert isinstance(node, GenericNDArrayNode) and node.can_preview()
        assert node.view == NDView((1, 2), (0,), 0, 1)
        node.set_view(None)
        images = [frame.get_native_object() for frame in node.frame_nodes()]
        assert [image.title.split()[0] for image in images] == [
            "cube[0,",
            "cube[1,",
        ]
        assert images[0].title.startswith("cube[0, :, :]")
        np.testing.assert_array_equal(images[1].data, np.arange(12, 24).reshape(3, 4))
        source = get_experimental_source(images[1])
        assert source["kind"] == "hdf5" and source["entry"] == "/cube"

        def no_selections(*_args) -> None:
            raise AssertionError("The selections of all frames were built")

        monkeypatch.setattr(NDView, "selections", no_selections)
        assert node.create_preview_object(4).data.shape == (2, 2)


def test_entry_and_default(tmp_path) -> None:
    """The default NXdata group follows the @default attributes."""

    def build(h5file: h5py.File) -> None:
        h5file.attrs["default"] = "entry"
        entry = h5file.create_group("entry")
        entry.attrs.update(NX_class="NXentry", default="data")
        entry["end_time"] = b"2026-10-27T10:00:00"
        group = entry.create_group("data")
        group.attrs.update(NX_class="NXdata", signal="y")
        group["y"] = np.ones(3)

    with _nodes_of(tmp_path, build) as nodes:
        node = nodes["/entry/data"]
        assert default_nxdata_path(node.h5file) == "/entry/data"
        assert entry_information(node.dset) == ({}, {"end": "2026-10-27T10:00:00"})
        assert default_nxdata_path(nodes["/"].h5file) == "/entry/data"


def test_compression_filters(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Compressed detector data is read with hdf5plugin; data compressed with an
    unavailable filter is reported instead of failing."""
    data = np.arange(64 * 32, dtype=np.uint32).reshape(64, 32)
    fname = str(tmp_path / "eiger.nxs")
    with h5py.File(fname, "w") as h5file:
        group = h5file.create_group("eiger")
        group.attrs.update(NX_class="NXdata", signal="data")
        group.create_dataset("data", data=data, **hdf5plugin.Bitshuffle(cname="lz4"))
    importer = H5Importer(fname)
    try:
        node = importer.get("/eiger")
        np.testing.assert_array_equal(node.get_native_object().data, data)
    finally:
        importer.close()
    available = h5py.h5z.filter_avail
    monkeypatch.setattr(
        h5py.h5z, "filter_avail", lambda code: code != 32008 and available(code)
    )
    importer = H5Importer(fname)
    try:
        node = importer.get("/eiger")
        assert not node.is_supported()
        assert "compressed with unavailable filter: bitshuffle" in node.text
        raw = importer.get("/eiger/data")
        assert not raw.is_supported()
        assert raw.text.startswith("<compressed with unavailable filter")
    finally:
        importer.close()


def test_mapping_leading_axes(tmp_path) -> None:
    """Mapping axes describe the first dimensions: signals of several ranks share
    one mapped object."""
    mapping = mapping_from_dict(
        {
            "version": 1,
            "name": "Scan",
            "match": {"paths": ["actuator_1_1"]},
            "objects": [
                {"name": "{name}", "signal": "data_*", "axes": ["actuator_1_1"]}
            ],
        }
    )
    with _nodes_of(tmp_path, _step_scan) as nodes:
        group = nodes["/scan_0494/scan_data"].dset
        described = dict(describe_mapping(mapping, group))
        assert [axis.name if axis else None for axis in described["data_02"].axes] == [
            "actuator_1_1",
            None,
        ]
        assert all(not desc.problems for desc in described.values())
        assert described["data_03"].shape == (3, 4, 5)
