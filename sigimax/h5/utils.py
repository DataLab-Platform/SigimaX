# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX Utilities for exogenous HDF5 format support
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

from typing import Any

import h5py
import numpy as np
from guidata.utils.misc import to_string


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
