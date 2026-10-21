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
from sigimax.h5.common import MAX_ATTRIBUTE_ITEMS, NODE_FACTORY, BaseNode
from sigimax.h5.generic import (
    GenericArrayNode,
    GenericCompoundNode,
    GenericScalarNode,
    GenericTextNode,
)

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
        h5file["cube"] = np.zeros((10, 30, 40))
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
        assert "/cube" not in nodes
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
        assert "/cube" not in [node.id for node in importer.nodes]
    finally:
        importer.close()
    assert triggered == ["/cube"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
