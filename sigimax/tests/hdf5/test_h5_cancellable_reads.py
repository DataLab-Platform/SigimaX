# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 cancellable read tests
---------------------------

Inside a ``cancellable_reads`` context, large regions of datasets are read in
blocks aligned on the dataset chunks, giving the same data as a direct read, and
the read stops at the next block once cancelled. Without context, regions are read
at once.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import h5py
import numpy as np
import pytest

from sigimax.h5 import utils
from sigimax.h5.utils import ReadCancelled, cancellable_reads, read_dataset

pytestmark = pytest.mark.unit

#: Block size used by the tests (elements)
BLOCK = 50


@pytest.fixture(name="h5file")
def fixture_h5file(tmp_path, monkeypatch) -> Generator[h5py.File, None, None]:
    """HDF5 file with chunked, contiguous and compound datasets"""
    monkeypatch.setattr(utils, "READ_BLOCK_ITEMS", BLOCK)
    fname = str(tmp_path / f"{uuid.uuid4()}.h5")
    with h5py.File(fname, "w") as h5file:
        h5file.create_dataset("chunked", data=np.arange(1000.0), chunks=(30,))
        h5file["contiguous"] = np.arange(1000, dtype=np.int16)
        h5file.create_dataset(
            "image", data=np.arange(60 * 70.0).reshape(60, 70), chunks=(7, 70)
        )
        h5file["cube"] = np.arange(4 * 30 * 40, dtype=np.uint16).reshape(4, 30, 40)
        records = np.zeros(400, dtype=[("x", "f8"), ("y", "i4")])
        records["x"], records["y"] = np.arange(400.0), np.arange(400)
        h5file["records"] = records
    with h5py.File(fname, "r") as h5file:
        yield h5file


@pytest.fixture(name="reads")
def fixture_reads(monkeypatch) -> list[tuple[str, object]]:
    """Record the reads of datasets (dataset path, selection)"""
    reads: list[tuple[str, object]] = []
    original = h5py.Dataset.__getitem__

    def getitem(dset, args, *rest, **kwargs):
        reads.append((dset.name, args))
        return original(dset, args, *rest, **kwargs)

    monkeypatch.setattr(h5py.Dataset, "__getitem__", getitem)
    return reads


REGIONS = [
    ("chunked", ()),
    ("chunked", slice(10, 900)),
    ("chunked", (slice(None, None, 3),)),
    ("contiguous", ()),
    ("contiguous", slice(5, 990, 7)),
    ("image", ()),
    ("image", (slice(3, 59), slice(None, None, 2))),
    ("image", (slice(None, None, 4), 5)),
    ("cube", ()),
    ("cube", (2, slice(None), slice(None))),
    ("cube", (slice(None), slice(1, 29, 2), np.int64(3))),
    ("records", ()),
    ("chunked", 3),
]


@pytest.mark.parametrize("name, region", REGIONS)
def test_block_reads_match_direct_reads(h5file, reads, name: str, region) -> None:
    """Regions read in blocks are equal to regions read at once"""
    dset = h5file[name]
    expected = dset[region]
    reads.clear()
    with cancellable_reads(lambda: False):
        data = read_dataset(dset, region)
    assert data.dtype == expected.dtype
    np.testing.assert_array_equal(data, expected)
    if np.size(expected) > BLOCK:
        assert len(reads) > 1
    else:
        assert len(reads) == 1


def test_blocks_are_aligned_on_chunks(h5file, reads) -> None:
    """With a unit step, block boundaries are multiples of the chunk size"""
    with cancellable_reads(lambda: False):
        read_dataset(h5file["chunked"], slice(10, 900))
    starts = [args[0].start for _name, args in reads]
    assert starts[0] == 10
    assert all(start % 30 == 0 for start in starts[1:])
    sizes = [args[0].stop - args[0].start for _name, args in reads]
    assert max(sizes) == 60  # BLOCK rounded up to a multiple of the chunk size


def test_cancelled_read_stops(h5file, reads) -> None:
    """A cancelled read stops at the next block"""
    with pytest.raises(ReadCancelled):
        with cancellable_reads(lambda: len(reads) >= 2):
            read_dataset(h5file["image"])
    assert len(reads) == 2
    reads.clear()
    with pytest.raises(ReadCancelled):
        with cancellable_reads(lambda: True):
            read_dataset(h5file["contiguous"], slice(0, 10))
    assert not reads


def test_reads_without_context_are_direct(h5file, reads) -> None:
    """Without context, regions are read at once, and the context is restored
    when it ends"""
    expected = h5file["image"][()]
    reads.clear()
    np.testing.assert_array_equal(read_dataset(h5file["image"]), expected)
    assert len(reads) == 1
    with pytest.raises(ReadCancelled):
        with cancellable_reads(lambda: True):
            read_dataset(h5file["image"])
    reads.clear()
    read_dataset(h5file["image"])
    assert len(reads) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
