# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 signal data type unit tests
--------------------------------

Signals imported from HDF5 datasets and NeXus ``NXdata`` groups keep the imaginary
part of complex data, and integers that cannot be represented exactly as floats
emit a warning instead of being rounded silently.
"""

from __future__ import annotations

import contextlib
import uuid
import warnings

import h5py
import numpy as np
import pytest
from sigima.objects import SignalObj

from sigimax.h5 import H5Importer

pytestmark = pytest.mark.unit

LARGE = 2**60 + 1

# NumPy >= 1.25 moved ComplexWarning to numpy.exceptions (and NumPy 2 removed the
# old location)
ComplexWarning = getattr(getattr(np, "exceptions", np), "ComplexWarning")


@pytest.fixture(name="nodes")
def fixture_nodes(tmp_path):
    """Nodes of a file with complex and large-integer signals, by path."""
    fname = str(tmp_path / f"{uuid.uuid4()}.h5")
    with h5py.File(fname, "w") as h5file:
        h5file["complex"] = (np.arange(5) + 1j * np.arange(5)).astype(np.complex64)
        h5file["large"] = np.array([LARGE, 1, 2], dtype=np.int64)
        h5file["counts"] = np.array([1, 2, 3], dtype=np.int32)
        h5file["table"] = (np.arange(10) + 1j).astype(np.complex64).reshape(2, 5)
        for name, data in (
            ("nx_complex", h5file["complex"][()]),
            ("nx_large", h5file["large"][()]),
        ):
            group = h5file.create_group(name)
            group.attrs["NX_class"] = "NXdata"
            group.attrs["signal"] = "data"
            group["data"] = data
    with contextlib.closing(H5Importer(fname)) as importer:
        yield {node.id: node for node in importer.nodes}


@pytest.mark.parametrize("path", ["/complex", "/nx_complex"])
def test_complex64_signal(nodes: dict, path: str) -> None:
    """Complex single-precision signals keep their imaginary part."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", ComplexWarning)
        obj = nodes[path].get_native_object()
    assert isinstance(obj, SignalObj)
    assert obj.y.dtype == np.complex128
    assert np.array_equal(obj.y, np.arange(5) + 1j * np.arange(5))


@pytest.mark.parametrize("path", ["/large", "/nx_large"])
def test_large_integer_signal(nodes: dict, path: str) -> None:
    """Integers beyond 2**53 are converted with a warning."""
    with pytest.warns(UserWarning, match="cannot be represented exactly"):
        obj = nodes[path].get_native_object()
    assert obj.y.dtype == np.float64
    assert obj.y[0] == float(LARGE)


def test_integer_signal_dtype(nodes: dict) -> None:
    """Integer signals are still imported as float64."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        obj = nodes["/counts"].get_native_object()
    assert obj.y.dtype == np.float64
    assert np.array_equal(obj.y, [1.0, 2.0, 3.0])


def test_complex_table_is_not_supported(nodes: dict) -> None:
    """Tables with complex X values are not imported, instead of being truncated."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", ComplexWarning)
        assert nodes["/table"].get_native_object() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
