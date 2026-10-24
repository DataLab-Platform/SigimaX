# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 lazy classification unit tests
-----------------------------------

Browsing an HDF5 file must not read whole datasets: nodes are classified and
described from the dataset shape and type, and textual previews read only the
first elements. Data is read entirely only when an object is created.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import h5py
import numpy as np
import pytest

from sigimax.h5 import H5Importer
from sigimax.h5.common import MAX_ATTRIBUTE_ITEMS, NODE_FACTORY, BaseNode, GroupNode
from sigimax.h5.generic import (
    GenericArrayNode,
    GenericCompoundNode,
    GenericNDArrayNode,
    GenericScalarNode,
    GenericTextNode,
)
from sigimax.h5.selection import NDSelection, preview_step, read_selection

pytestmark = pytest.mark.unit

#: Datasets larger than this must never be read entirely while browsing
FULL_READ_LIMIT = 1000


@pytest.fixture(name="h5fname")
def fixture_h5fname(tmp_path) -> str:
    """HDF5 file covering the generic node kinds, with large datasets."""
    fname = str(tmp_path / f"{uuid.uuid4()}.h5")
    with h5py.File(fname, "w") as h5file:
        h5file["scalar"] = np.int32(5)
        h5file["text"] = "unicode text"
        h5file["signal"] = np.arange(50_000.0)
        h5file["image"] = np.ones((300, 400), dtype=np.uint16)
        counts = [[0, 2**32 - 1, 3], [7, 2**31, 4], [1, 2, 5]]
        h5file["counts"] = np.array(counts, np.uint32)
        h5file["cube"] = np.arange(10 * 30 * 40, dtype=np.float64).reshape(10, 30, 40)
        records = np.zeros(5000, dtype=[("x", "f8"), ("y", "f4")])
        h5file["records"] = records
        mixed = np.zeros(5000, dtype=[("name", "S8"), ("v", "f8")])
        mixed["name"] = b"label"
        h5file["mixed"] = mixed
        h5file["signal"].attrs["unit"] = "s"
        h5file["signal"].attrs["big"] = np.zeros(MAX_ATTRIBUTE_ITEMS + 1, np.uint8)
    return fname


@pytest.fixture(name="full_reads")
def fixture_full_reads(monkeypatch) -> Generator[list[str], None, None]:
    """Record whole reads of datasets larger than :data:`FULL_READ_LIMIT`."""
    reads: list[str] = []
    original = h5py.Dataset.__getitem__

    def getitem(self, args, *rest, **kwargs):
        selection = args if isinstance(args, tuple) else (args,)
        whole = selection in ((), (Ellipsis,)) or all(
            isinstance(item, slice) and item == slice(None) for item in selection
        )
        if whole and self.size > FULL_READ_LIMIT:
            reads.append(self.name)
        return original(self, args, *rest, **kwargs)

    monkeypatch.setattr(h5py.Dataset, "__getitem__", getitem)
    yield reads


def test_browsing_reads_no_large_dataset(h5fname: str, full_reads: list) -> None:
    """Classification and descriptions use metadata and bounded reads only."""
    importer = H5Importer(h5fname)
    try:
        nodes = {node.id: node for node in importer.nodes}
        for node in nodes.values():
            _description = (
                node.shape_str,
                node.dtype_str,
                node.text,
                node.icon_name,
                node.is_supported(),
                node.metadata,
            )
        assert full_reads == []
        assert isinstance(nodes["/scalar"], GenericScalarNode)
        assert isinstance(nodes["/text"], GenericTextNode)
        assert isinstance(nodes["/records"], GenericArrayNode)
        assert isinstance(nodes["/mixed"], GenericCompoundNode)
        assert isinstance(nodes["/cube"], GenericNDArrayNode)
        assert nodes["/cube"].shape_str == "10 x 30 x 40"
        assert not nodes["/cube"].is_supported()
        assert nodes["/signal"].shape_str == "50000"
        assert nodes["/signal"].text.endswith(" ...")
        assert nodes["/records"].shape_str == "5000 x 2"
        assert nodes["/records"].dtype_str == "float64"
        assert nodes["/image"].icon_name == "image.svg"
        assert nodes["/mixed"].text.endswith("...]")
        assert nodes["/signal"].metadata["unit"] == "s"
        assert "big" not in nodes["/signal"].metadata

        # Creating the object reads the whole dataset, on demand
        signal = nodes["/signal"].get_native_object()
        assert full_reads == ["/signal"]
        assert signal.y.size == 50_000
    finally:
        importer.close()


def test_uint32_image_is_exact(h5fname: str) -> None:
    """uint32 counts beyond the int32 range are imported without clipping."""
    importer = H5Importer(h5fname)
    try:
        node = importer.get("/counts")
        assert node.icon_name == "image.svg"
        image = node.get_native_object()
        assert image.data.dtype == np.float64
        assert image.data[0, 1] == 2**32 - 1
        assert image.data[1, 1] == 2**31
        assert not node.uint32_wng
    finally:
        importer.close()


def test_broken_links_are_skipped(tmp_path, capsys) -> None:
    """Files with broken soft or external links (e.g. synchrotron master files
    without their detector files) are opened: the broken links are skipped."""
    fname = str(tmp_path / f"{uuid.uuid4()}.nxs")
    with h5py.File(fname, "w") as h5file:
        entry = h5file.create_group("entry")
        entry["signal"] = np.arange(10.0)
        entry["dangling_soft"] = h5py.SoftLink("/entry/missing")
        entry["dangling_external"] = h5py.ExternalLink("missing.h5", "/data")
        h5file["root_link"] = h5py.SoftLink("/missing")
        detector = entry.create_group("detector")
        detector.attrs.update({"NX_class": "NXdata", "signal": "frames"})
        detector["frames"] = h5py.ExternalLink("missing_detector.h5", "/frames")
    importer = H5Importer(fname)
    try:
        ids = {node.id for node in importer.nodes}
        assert {"/entry", "/entry/signal", "/entry/detector"} <= ids
        assert not ids & {
            "/entry/dangling_soft",
            "/entry/dangling_external",
            "/root_link",
            "/entry/detector/frames",
        }
        assert importer.get("/entry/signal").get_native_object().y.size == 10
        assert not importer.get("/entry/detector").is_supported()
    finally:
        importer.close()
    output = capsys.readouterr().out
    assert "'/entry/dangling_soft': broken soft link to '/entry/missing'" in output
    assert "'/root_link': broken soft link" in output
    assert "broken external link to 'missing.h5:/data'" in output


def test_link_cycles_are_skipped(tmp_path, capsys) -> None:
    """Links back to a parent group are skipped instead of being collected forever,
    while other aliases of a group or a dataset are kept at each of their paths.

    Regression: a group linked into itself raised a RecursionError.
    """
    fname = str(tmp_path / f"{uuid.uuid4()}.h5")
    with h5py.File(fname, "w") as h5file:
        entry = h5file.create_group("entry")
        entry["signal"] = np.arange(10.0)
        entry["self"] = entry  # hard link to itself
        inner = entry.create_group("inner")
        inner["up"] = entry  # hard link to its parent (two-group cycle)
        inner["root"] = h5py.SoftLink("/")  # soft link to the root group
        h5file["alias"] = entry["signal"]  # dataset alias, not a cycle
        h5file["entry_alias"] = inner  # group alias, not a cycle
    importer = H5Importer(fname)
    try:
        ids = {node.id for node in importer.nodes}
        # The group alias is kept, with its own path to the parent group of the
        # aliased group (which is not one of its own parents)
        assert ids == {
            "/",
            "/entry",
            "/entry/signal",
            "/entry/inner",
            "/alias",
            "/entry_alias",
            "/entry_alias/up",
            "/entry_alias/up/signal",
        }
        assert importer.get("/alias").get_native_object().y.size == 10
    finally:
        importer.close()
    output = capsys.readouterr().out
    assert "'/entry/self': link back to its parent group '/entry'" in output
    assert "'/entry/inner/up': link back to its parent group '/entry'" in output
    assert "'/entry/inner/root': link back to its parent group '/'" in output


def test_importer_closes_file_on_failure(tmp_path, monkeypatch) -> None:
    """The HDF5 file is closed when the tree cannot be built."""
    fname = str(tmp_path / f"{uuid.uuid4()}.h5")
    with h5py.File(fname, "w") as h5file:
        h5file["signal"] = np.arange(10.0)
    opened: list[h5py.File] = []
    original_file = h5py.File

    def spy_file(*args, **kwargs):
        opened.append(original_file(*args, **kwargs))
        return opened[-1]

    def fail(*_args, **_kwargs):
        raise RuntimeError("tree failure")

    monkeypatch.setattr(h5py, "File", spy_file)
    monkeypatch.setattr(GroupNode, "collect_children", fail)
    with pytest.raises(RuntimeError, match="tree failure"):
        H5Importer(fname)
    assert len(opened) == 1 and not opened[0].id.valid


def test_unregister_node_class(h5fname: str) -> None:
    """A node class registered by an application can be removed again."""

    class CubeNode(BaseNode):
        """Node matching the 3D dataset only."""

        @classmethod
        def match(cls, dset):
            return isinstance(dset, h5py.Dataset) and dset.ndim == 3

    triggered: list[str] = []
    NODE_FACTORY.register(CubeNode)
    NODE_FACTORY.add_post_trigger(
        CubeNode, lambda node, _imp: triggered.append(node.id)
    )
    try:
        importer = H5Importer(h5fname)
        assert isinstance(importer.get("/cube"), CubeNode)
        importer.close()
    finally:
        NODE_FACTORY.unregister(CubeNode)
    NODE_FACTORY.unregister(CubeNode)
    importer = H5Importer(h5fname)
    try:
        assert isinstance(importer.get("/cube"), GenericNDArrayNode)
    finally:
        importer.close()
    assert triggered == ["/cube"]


def test_read_selection(h5fname: str, full_reads: list) -> None:
    """Selected views of a cube match NumPy indexing, without reading the cube."""
    with h5py.File(h5fname, "r") as h5file:
        dset = h5file["cube"]
        cube = np.arange(10 * 30 * 40, dtype=np.float64).reshape(10, 30, 40)
        frame = read_selection(dset, NDSelection((1, 2), (4,)))
        assert np.array_equal(frame, cube[4])
        transposed = read_selection(dset, NDSelection((2, 1), (4,)))
        assert np.array_equal(transposed, cube[4].T)
        spectrum = read_selection(dset, NDSelection((0,), (7, 3)))
        assert np.array_equal(spectrum, cube[:, 7, 3])
        strided = read_selection(dset, NDSelection((1, 2), (0,)), step=3)
        assert np.array_equal(strided, cube[0, ::3, ::3])
        assert NDSelection((0,), (7, 3)).as_dict() == {
            "displayed": [0],
            "indices": [7, 3],
        }
        for invalid in (
            NDSelection((0, 1, 2)),
            NDSelection((1, 1), (0,)),
            NDSelection((1, 2)),
            NDSelection((1, 2), (10,)),
        ):
            with pytest.raises(ValueError):
                read_selection(dset, invalid)
    assert full_reads == []


@pytest.mark.parametrize(
    "shape, max_items, step",
    [
        ((100,), 100, 1),
        ((101,), 100, 2),
        ((4096, 4096), 2**24, 1),
        ((300, 400), 1000, 12),
        ((3, 100_000_000), 1000, 100_000),
        ((2, 10**10), 2**24, 597),
        ((0, 400), 10, 1),
        ((), 1, 1),
    ],
    ids=["fits", "1d", "2d-fits", "2d", "asymmetric", "huge", "empty", "scalar"],
)
def test_preview_step(shape: tuple, max_items: int, step: int) -> None:
    """The preview step is the smallest one keeping the view under the limit."""
    assert preview_step(shape, max_items) == step
    sizes = [len(range(0, dim, step)) for dim in shape]
    assert np.prod(sizes) <= max_items
    if step > 1:
        sizes = [len(range(0, dim, step - 1)) for dim in shape]
        assert np.prod(sizes) > max_items


def test_preview_is_decimated(h5fname: str, full_reads: list) -> None:
    """Previews of large datasets are read with a step, in physical coordinates."""
    importer = H5Importer(h5fname)
    try:
        image = importer.get("/image").create_preview_object(1000)
        assert image.data.shape == (25, 34)
        assert (image.dx, image.dy) == (12.0, 12.0)
        signal = importer.get("/signal").create_preview_object(1000)
        assert signal.y.size <= 1000
        assert np.array_equal(signal.x, signal.y)
        assert full_reads == []
        small = importer.get("/counts")
        assert small.create_preview_object(1000) is small.get_native_object()
    finally:
        importer.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
