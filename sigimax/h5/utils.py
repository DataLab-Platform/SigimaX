# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX Utilities for exogenous HDF5 format support
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

import math
import os.path as osp
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

import h5py
import numpy as np
from guidata.utils.misc import to_string


def split_h5_file_selector(selector: str) -> tuple[str, str | None]:
    """Split an HDF5 file selector into a file name and a dataset name

    A selector is a file name, optionally followed by a comma and the name of the
    dataset to import (e.g. ``"data.h5,/entry/counts"``). A selector naming an
    existing file is a file name, even if it contains commas, and the file name
    of a dataset selector may contain commas if it names an existing file.

    Args:
        selector: file name, or file name and dataset name separated by a comma

    Returns:
        File name and dataset name (None if the selector is a file name)

    Raises:
        ValueError: if the selector has several commas and its part before the
         last comma is not an existing file
    """
    if "," not in selector or osp.isfile(selector):
        return selector, None
    filename, dsetname = selector.rsplit(",", 1)
    if "," in filename and not osp.isfile(filename):
        raise ValueError(
            f"Invalid HDF5 file selector {selector!r}: expected a file name, "
            "optionally followed by a comma and a dataset name"
        )
    return filename, dsetname


def fix_ldata(fuzzy):
    """Fix label data"""
    if fuzzy is not None:
        if fuzzy and isinstance(fuzzy, np.void) and len(fuzzy) > 1:
            #  Shouldn't happen (invalid LMJ fmt)
            fuzzy = fuzzy[0]
        if isinstance(fuzzy, (np.bytes_, bytes)):
            fuzzy = to_string(fuzzy)
        if isinstance(fuzzy, str):
            return fuzzy
    return ""


def fix_ndata(fuzzy):
    """Fix numeric data"""
    if fuzzy is not None:
        if fuzzy and isinstance(fuzzy, np.void) and len(fuzzy) > 1:
            #  Shouldn't happen (invalid LMJ fmt)
            fuzzy = fuzzy[0]
        try:
            if float(fuzzy) == int(fuzzy):
                return int(fuzzy)
            return float(fuzzy)
        except (TypeError, ValueError):
            pass
    return None


def process_scalar_value(dset, name, callback):
    """Process dataset numeric/str value `name`"""
    try:
        scdata = dset[name][()]
        if isinstance(scdata, np.ndarray):
            scdata = scdata[0]
        if scdata is not None:
            return callback(scdata)
    except (KeyError, ValueError):
        pass
    return None


def process_label(dset, name):
    """Process dataset label `name`"""
    try:
        ldata = dset[name][()]
        if ldata is not None:
            xldata, yldata, zldata = "", "", ""
            if len(ldata) == 2:
                xldata, yldata = ldata
            elif len(ldata) == 3:
                xldata, yldata, zldata = ldata
            return fix_ldata(xldata), fix_ldata(yldata), fix_ldata(zldata)
    except KeyError:
        pass
    return "", "", ""


def process_xy_values(dset, name):
    """Process dataset x,y values `name`"""
    try:
        ldata = dset[name][()]
        if ldata is not None:
            return fix_ndata(ldata[0]), fix_ndata(ldata[1])
    except (KeyError, ValueError):
        pass
    return None, None


def is_supported_num_dtype(data):
    """Return True if data type is a numerical type supported by SigimaX"""
    return data.dtype.name.startswith(("int", "uint", "float", "complex"))


def is_single_str_array(data):
    """Return True if data is a single-item string array"""
    return (
        isinstance(data, np.generic) and data.shape == (1,) and isinstance(data[0], str)
    )


def is_supported_str_dtype(data):
    """Return True if data type is a string type supported by preview"""
    return data.dtype.name.startswith("string") or is_single_str_array(data)


def is_string_dtype(dtype: np.dtype) -> bool:
    """Return True if dtype stores fixed-length or variable-length strings"""
    return dtype.kind in "SU" or h5py.check_string_dtype(dtype) is not None


def get_size(dset: h5py.Dataset) -> int:
    """Return the number of elements of a dataset, without reading it"""
    return 0 if dset.shape is None else int(np.prod(dset.shape, dtype=np.int64))


def unavailable_filters(dset: h5py.Dataset) -> list[str]:
    """Return the compression filters of a dataset that HDF5 cannot apply

    Such datasets cannot be read. Filters of detector data (bitshuffle/LZ4,
    Blosc...) are made available by hdf5plugin, imported with :mod:`sigimax.h5`.

    Args:
        dset: HDF5 dataset

    Returns:
        Name and identifier of each unavailable filter, e.g. ``"bitshuffle (32008)"``
    """
    plist = dset.id.get_create_plist()
    names = []
    for index in range(plist.get_nfilters()):
        code, _flags, _values, name = plist.get_filter(index)
        if not h5py.h5z.filter_avail(code):
            text = to_string(name).strip() or "filter"
            names.append(f"{text} ({code})")
    return names


#: Number of elements above which reads of a :func:`cancellable_reads` context
#: are made in blocks (of about this number of elements)
READ_BLOCK_ITEMS = 2**18

_IS_CANCELLED: ContextVar[Callable[[], bool] | None] = ContextVar(
    "sigimax_h5_is_cancelled", default=None
)


class ReadCancelled(BaseException):
    """Raised by :func:`read_dataset` when a read of a :func:`cancellable_reads`
    context is cancelled

    Like :class:`asyncio.CancelledError`, it derives from :class:`BaseException`,
    so that ``except Exception`` clauses of code reading data do not take a
    cancelled read for invalid data.
    """


@contextmanager
def cancellable_reads(is_cancelled: Callable[[], bool]) -> Iterator[None]:
    """Make the dataset reads of the current thread cancellable

    Inside this context, :func:`read_dataset` reads regions larger than
    :data:`READ_BLOCK_ITEMS` elements in blocks (aligned on the chunks of the
    dataset), and raises :class:`ReadCancelled` before reading a block, or a
    small region, once ``is_cancelled()`` returns True. Use it in a worker thread
    reading data which may no longer be needed (e.g. the preview of a node, once
    another node is selected): h5py serializes HDF5 calls with a global lock, so
    that the other threads reading HDF5 files wait for the whole read otherwise.

    Args:
        is_cancelled: function returning True once the reads are to be stopped
         (called from the reading thread)
    """
    token = _IS_CANCELLED.set(is_cancelled)
    try:
        yield
    finally:
        _IS_CANCELLED.reset(token)


def read_dataset(dset: h5py.Dataset, region: Any = ()) -> Any:
    """Read a region of a dataset, reporting read errors with the dataset path

    Inside a :func:`cancellable_reads` context, large regions are read in blocks,
    and the read is stopped (:class:`ReadCancelled`) once cancelled.

    Args:
        dset: HDF5 dataset
        region: selection passed to ``dset[...]`` (default: whole dataset)

    Returns:
        Data that was read

    Raises:
        OSError: if HDF5 cannot read the data (truncated or corrupted file,
         missing external file, read error on a network drive...)
        ReadCancelled: if the read was cancelled (see :func:`cancellable_reads`)
    """
    is_cancelled = _IS_CANCELLED.get()
    try:
        if is_cancelled is None:
            return dset[region]
        return _read_cancellable(dset, region, is_cancelled)
    except OSError as exc:
        fname = osp.basename(dset.file.filename)
        raise OSError(f"Unable to read dataset '{dset.name}' ({fname}): {exc}") from exc


def _block_regions(
    dset: h5py.Dataset, region: Any
) -> tuple[tuple[int, ...], list[tuple[tuple, tuple]]] | None:
    """Return the blocks in which a region of a dataset is read

    Blocks are stacked along the first axis of the read data with more than one
    element. With a unit step along this axis, block boundaries are multiples of
    the chunk size of the dataset, so that chunks are not decompressed twice.

    Args:
        dset: HDF5 dataset
        region: selection passed to ``dset[...]``

    Returns:
        Shape of the read data, and for each block, its position in the read
        data and its selection in the dataset; None if the region is to be read at
        once (region of at most :data:`READ_BLOCK_ITEMS` elements, or selection
        not made of indices and slices)
    """
    shape = dset.shape
    if not shape:
        return None
    if not isinstance(region, tuple):
        region = (region,)
    if len(region) > len(shape):
        return None
    region = region + (slice(None),) * (len(shape) - len(region))
    ranges: list[range | None] = []
    for item, size in zip(region, shape):
        if isinstance(item, slice):
            ranges.append(range(*item.indices(size)))
        elif isinstance(item, (int, np.integer)) and not isinstance(item, bool):
            ranges.append(None)
        else:
            return None
    out_shape = tuple(len(rng) for rng in ranges if rng is not None)
    total = math.prod(out_shape)
    if not out_shape or total <= READ_BLOCK_ITEMS:
        return None
    axis = next(
        index for index, rng in enumerate(ranges) if rng is not None and len(rng) > 1
    )
    rng = ranges[axis]
    rows = max(1, READ_BLOCK_ITEMS // (total // len(rng)))
    first = rows
    if rng.step == 1 and dset.chunks is not None:
        chunk = dset.chunks[axis]
        rows = -(-rows // chunk) * chunk
        first = (rng.start // rows + 1) * rows - rng.start
    edges = [0, *range(first, len(rng), rows), len(rng)]
    out_axis = sum(1 for other in ranges[:axis] if other is not None)
    blocks = []
    for start, stop in zip(edges[:-1], edges[1:]):
        selection = list(region)
        selection[axis] = slice(rng[start], rng[stop - 1] + 1, rng.step)
        position = (slice(None),) * out_axis + (slice(start, stop),)
        blocks.append((position, tuple(selection)))
    return out_shape, blocks


def _read_cancellable(
    dset: h5py.Dataset, region: Any, is_cancelled: Callable[[], bool]
) -> Any:
    """Read a region of a dataset, in blocks if it is large, until cancelled

    Raises:
        ReadCancelled: if ``is_cancelled()`` returns True before a block is read
    """
    if is_cancelled():
        raise ReadCancelled
    layout = _block_regions(dset, region)
    if layout is None:
        return dset[region]
    out_shape, blocks = layout
    data = None
    for index, (position, selection) in enumerate(blocks):
        if index and is_cancelled():
            raise ReadCancelled
        block = dset[selection]
        if data is None:
            data = np.empty(out_shape, dtype=block.dtype)
        data[position] = block
    return data


def read_bounded(dset: h5py.Dataset, max_items: int) -> tuple[Any, bool]:
    """Read the first elements of a dataset, along each axis

    Args:
        dset: HDF5 dataset
        max_items: maximum number of elements to read

    Returns:
        Data that was read and True if it is only part of the dataset
    """
    shape = dset.shape
    if not shape or get_size(dset) <= max_items:
        return dset[()], False
    per_axis = max(1, int(max_items ** (1 / len(shape))))
    return dset[tuple(slice(0, min(size, per_axis)) for size in shape)], True


def read_first_items(dset: h5py.Dataset, count: int) -> tuple[Any, bool]:
    """Read the first elements of a dataset, in C order, from its first row

    Args:
        dset: HDF5 dataset with at least one dimension
        count: maximum number of elements to read

    Returns:
        Data that was read and True if it is only part of the dataset
    """
    selection = (0,) * (len(dset.shape) - 1) + (slice(0, count),)
    return dset[selection], get_size(dset) > count
