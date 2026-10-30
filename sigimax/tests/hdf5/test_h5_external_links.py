# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 external links unit tests
------------------------------

Objects reached through an external link (e.g. the detector data of synchrotron
master files) are shown and imported at their path in the opened file: their
path in their own file (``dset.name``) may not exist in the opened file, or may
designate another object there.
"""

from __future__ import annotations

import h5py
import numpy as np
import pytest
from sigima.objects import ImageObj, get_experimental_source

from sigimax.h5 import H5Importer
from sigimax.h5.generic import GenericArrayNode, GenericNDArrayNode
from sigimax.h5.nexus import AuxiliarySignalNode, NXdataNode, default_nxdata_path

pytestmark = pytest.mark.unit


@pytest.fixture(name="master")
def fixture_master(tmp_path) -> str:
    """Master file linking to two detector files, like those of Eiger detectors,
    and to an ``NXdata`` group and a cube of an analysis file."""
    for index, value in ((1, 1.0), (2, 2.0)):
        with h5py.File(tmp_path / f"data_{index:06d}.h5", "w") as h5file:
            h5file["/entry/data/data"] = np.full((4, 5), value)
    with h5py.File(tmp_path / "analysis.h5", "w") as h5file:
        group = h5file.create_group("result")
        group.attrs.update(
            NX_class="NXdata", signal="map", auxiliary_signals=["error_map"]
        )
        group["map"] = np.arange(12.0).reshape(3, 4)
        group["error_map"] = np.ones((3, 4))
        h5file["cube"] = np.arange(2 * 3 * 4, dtype=float).reshape(2, 3, 4)
    fname = str(tmp_path / "master.h5")
    with h5py.File(fname, "w") as h5file:
        h5file.attrs["default"] = "entry"
        entry = h5file.create_group("entry")
        entry.attrs.update(NX_class="NXentry", default="analysis")
        data = entry.create_group("data")
        # Same path as the datasets of the detector files, in the master file
        data["data"] = np.zeros(3)
        for index in (1, 2):
            data[f"data_{index:06d}"] = h5py.ExternalLink(
                f"data_{index:06d}.h5", "/entry/data/data"
            )
        entry["analysis"] = h5py.ExternalLink("analysis.h5", "/result")
        entry["cube"] = h5py.ExternalLink("analysis.h5", "/cube")
    return fname


def test_external_datasets_keep_master_paths(master: str) -> None:
    """Datasets of other files are shown and imported at their master path.

    Regression: they were collected at their path in their own file, which is
    missing from the master file (the datasets were skipped) or designates
    another dataset of the master file (whose data was imported instead).
    """
    importer = H5Importer(master)
    try:
        nodes = {node.id: node for node in importer.nodes}
        assert {
            "/entry/data/data",
            "/entry/data/data_000001",
            "/entry/data/data_000002",
        } <= set(nodes)
        assert nodes["/entry/data/data"].get_native_object().y.size == 3
        for index, value in ((1, 1.0), (2, 2.0)):
            node = nodes[f"/entry/data/data_{index:06d}"]
            assert isinstance(node, GenericArrayNode)
            assert node.name == f"data_{index:06d}"
            image = node.get_native_object()
            assert isinstance(image, ImageObj)
            np.testing.assert_array_equal(image.data, np.full((4, 5), value))
            assert image.get_metadata_option("HDF5Dataset") == node.id
        assert [child.id for child in nodes["/entry/data"].children] == [
            "/entry/data/data",
            "/entry/data/data_000001",
            "/entry/data/data_000002",
        ]
    finally:
        importer.close()


def test_external_nexus_group_keeps_master_path(master: str) -> None:
    """An ``NXdata`` group of another file, its auxiliary signals, the frames of
    a cube of another file and the default ``NXdata`` group designated through
    an external link are identified by their master paths."""
    importer = H5Importer(master)
    try:
        nodes = {node.id: node for node in importer.nodes}
        assert "/result" not in nodes and "/cube" not in nodes
        group = nodes["/entry/analysis"]
        assert isinstance(group, NXdataNode) and group.name == "analysis"
        assert {"/entry/analysis/map", "/entry/analysis/error_map"} <= set(nodes)
        source = get_experimental_source(group.get_native_object())
        assert source["entry"] == "/entry/analysis"
        assert source["location"] == master
        auxiliary = nodes["/entry/analysis::error_map"]
        assert isinstance(auxiliary, AuxiliarySignalNode)
        assert get_experimental_source(auxiliary.get_native_object())["entry"] == (
            "/entry/analysis"
        )
        assert default_nxdata_path(importer.h5file) == "/entry/analysis"

        cube = nodes["/entry/cube"]
        assert isinstance(cube, GenericNDArrayNode)
        cube.set_view(None)
        frames = cube.frame_nodes()
        assert [frame.h5path for frame in frames] == ["/entry/cube"] * 2
        image = frames[1].get_native_object()
        np.testing.assert_array_equal(image.data, np.arange(12, 24).reshape(3, 4))
        assert get_experimental_source(image)["entry"] == "/entry/cube"
    finally:
        importer.close()


def test_relative_node_paths(tmp_path) -> None:
    """Node paths are absolute, whatever the path given to create a node."""
    fname = str(tmp_path / "relative.h5")
    with h5py.File(fname, "w") as h5file:
        h5file["/entry/signal"] = np.arange(4.0)
    with h5py.File(fname, "r") as h5file:
        for dname in ("entry/signal", "/entry/signal", "/entry/signal/"):
            node = GenericArrayNode(h5file, dname)
            assert (node.id, node.name) == ("/entry/signal", "signal")
