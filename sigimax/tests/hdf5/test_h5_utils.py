# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for HDF5 utility modules
-------------------------------

Covers:
- h5/common.py: data_to_xy with various shaped arrays
- h5/generic.py: safe_decode_bytes, format_text_data
- h5/utils.py: fix_ldata, fix_ndata, is_single_str_array, is_supported_num_dtype,
  is_supported_str_dtype, process_scalar_value, process_label, process_xy_values
"""

from __future__ import annotations

import h5py
import numpy as np
import pytest

from sigimax.h5.common import data_to_xy
from sigimax.h5.generic import format_text_data, safe_decode_bytes
from sigimax.h5.utils import (
    fix_ldata,
    fix_ndata,
    is_single_str_array,
    is_supported_num_dtype,
    is_supported_str_dtype,
    process_label,
    process_scalar_value,
    process_xy_values,
)

pytestmark = pytest.mark.unit


# ======================== data_to_xy =========================================


class TestDataToXy:
    """Tests for data_to_xy conversion."""

    def test_1d_array(self):
        """1D array should be treated as y values with x as indices."""
        data = np.array([10, 20, 30])
        x, y, dx, dy = data_to_xy(data)
        np.testing.assert_array_equal(x, np.arange(3))
        np.testing.assert_array_equal(y, data)
        assert dx is None
        assert dy is None

    def test_2col_array(self):
        """2D array with 2 columns should be treated as x and y."""
        data = np.array([[1, 4], [2, 5], [3, 6]])
        x, y, dx, dy = data_to_xy(data)
        np.testing.assert_array_equal(x, [1, 2, 3])
        np.testing.assert_array_equal(y, [4, 5, 6])
        assert dx is None
        assert dy is None

    def test_3col_array(self):
        """3D array with 3 columns should be treated as x, y, and dy."""
        # rows > cols triggers transpose: 5×3 → 3×5
        data = np.array(
            [[1, 4, 0.1], [2, 5, 0.2], [3, 6, 0.3], [4, 7, 0.4], [5, 8, 0.5]]
        )
        x, y, dx, dy = data_to_xy(data)
        np.testing.assert_array_equal(x, [1, 2, 3, 4, 5])
        np.testing.assert_array_equal(y, [4, 5, 6, 7, 8])
        assert dx is None
        np.testing.assert_array_almost_equal(dy, [0.1, 0.2, 0.3, 0.4, 0.5])

    def test_4col_array(self):
        """4D array with 4 columns should be treated as x, y, dx, and dy."""
        # rows > cols triggers transpose: 5×4 → 4×5
        data = np.array(
            [
                [1, 4, 0.1, 0.4],
                [2, 5, 0.2, 0.5],
                [3, 6, 0.3, 0.6],
                [4, 7, 0.4, 0.7],
                [5, 8, 0.5, 0.8],
            ]
        )
        x, y, dx, dy = data_to_xy(data)
        np.testing.assert_array_equal(x, [1, 2, 3, 4, 5])
        np.testing.assert_array_equal(y, [4, 5, 6, 7, 8])
        np.testing.assert_array_almost_equal(dx, [0.1, 0.2, 0.3, 0.4, 0.5])
        np.testing.assert_array_almost_equal(dy, [0.4, 0.5, 0.6, 0.7, 0.8])

    def test_2row_array_transposed(self):
        """2 rows × many cols should be transposed."""
        data = np.array([[1, 2, 3, 4, 5], [10, 20, 30, 40, 50]])
        x, y, _dx, _dy = data_to_xy(data)
        np.testing.assert_array_equal(x, [1, 2, 3, 4, 5])
        np.testing.assert_array_equal(y, [10, 20, 30, 40, 50])

    def test_invalid_shape_raises(self):
        """Arrays with unsupported shapes should raise an error."""
        data = np.ones((5, 5, 5))
        with pytest.raises((ValueError, IndexError)):
            data_to_xy(data)


# ======================== safe_decode_bytes ==================================


class TestSafeDecodeBytes:
    """Tests for safe_decode_bytes."""

    def test_str_passthrough(self):
        """String input should be returned unchanged."""
        assert safe_decode_bytes("hello") == "hello"

    def test_bytes_utf8(self):
        """UTF-8 encoded bytes should be decoded to a string."""
        assert safe_decode_bytes(b"hello") == "hello"

    def test_bytes_latin1(self):
        """Bytes that are not valid UTF-8 should be decoded with latin1 fallback."""
        result = safe_decode_bytes("café".encode("latin1"))
        assert "caf" in result

    def test_none_returns_str(self):
        """None input should be converted to an empty string."""
        result = safe_decode_bytes(None)
        assert isinstance(result, str)

    def test_int_returns_str(self):
        """Non-string, non-bytes input should be converted to string."""
        result = safe_decode_bytes(42)
        assert result == "42"


# ======================== format_text_data ===================================


class TestFormatTextData:
    """Tests for format_text_data."""

    def test_none_returns_unreadable(self):
        """None input should return a string indicating the data is unreadable."""
        result = format_text_data(None)
        assert "unreadable" in result.lower()

    def test_string_passthrough(self):
        """String input should be returned unchanged."""
        result = format_text_data("some text")
        assert "some text" in result

    def test_numeric(self):
        """Numeric input should be converted to string."""
        result = format_text_data(42)
        assert "42" in result


# ======================== fix_ldata / fix_ndata ==============================


class TestFixFunctions:
    """Tests for fix_ldata and fix_ndata."""

    def test_fix_ldata_string(self):
        """String input should be returned unchanged."""
        assert fix_ldata("hello") == "hello"

    def test_fix_ldata_bytes(self):
        """Bytes input should be decoded to a string."""
        result = fix_ldata(np.bytes_(b"test"))
        assert result == "test"

    def test_fix_ldata_none(self):
        """None input should be converted to an empty string."""
        assert fix_ldata(None) == ""

    def test_fix_ndata_int(self):
        """Integer input should be returned unchanged."""
        assert fix_ndata(5) == 5

    def test_fix_ndata_float(self):
        """Float input should be returned unchanged."""
        assert fix_ndata(3.14) == 3.14

    def test_fix_ndata_none(self):
        """None input should be returned unchanged."""
        assert fix_ndata(None) is None

    def test_fix_ndata_string(self):
        """String input should be converted to None."""
        assert fix_ndata("not a number") is None


# ======================== dtype checks =======================================


class TestDtypeChecks:
    """Tests for is_supported_num_dtype and is_supported_str_dtype."""

    def test_int_dtype(self):
        """Integer dtype should be supported."""
        data = np.array([1, 2, 3], dtype=np.int32)
        assert is_supported_num_dtype(data) is True

    def test_float_dtype(self):
        """Float dtype should be supported."""
        data = np.array([1.0, 2.0], dtype=np.float64)
        assert is_supported_num_dtype(data) is True

    def test_complex_dtype(self):
        """Complex dtype should be supported."""
        data = np.array([1 + 2j], dtype=np.complex128)
        assert is_supported_num_dtype(data) is True

    def test_bool_dtype_not_num(self):
        """Boolean dtype should not be considered a supported numeric dtype."""
        data = np.array([True, False])
        assert is_supported_num_dtype(data) is False

    def test_uint_dtype(self):
        """Unsigned integer dtype should be supported."""
        data = np.array([1, 2], dtype=np.uint16)
        assert is_supported_num_dtype(data) is True

    def test_is_single_str_array_false_for_generic_scalar(self):
        """An ``ndarray`` (not a numpy generic) is rejected."""
        scalar = np.array(["x"], dtype=str)[0:1]  # ndarray, not generic
        assert is_single_str_array(scalar) is False

    def test_is_single_str_array_false_for_ndarray(self):
        """A multi-element ndarray of strings is not a single string array."""
        arr = np.array(["a", "b"])
        assert is_single_str_array(arr) is False

    def test_supported_str_dtype_false_for_bytes_array(self):
        """NumPy bytes-dtype arrays are not classified as string-supported."""
        arr = np.array([b"x", b"y"], dtype="S2")
        # numpy bytes dtype name starts with "bytes" not "string" -> expected False
        assert is_supported_str_dtype(arr) is False

    def test_supported_str_dtype_false_for_int(self):
        """Numeric arrays are not string-supported."""
        assert is_supported_str_dtype(np.zeros(3, dtype=np.int32)) is False


# ======================== process_scalar_value / process_label / process_xy ==


@pytest.fixture(name="h5_with_datasets")
def _h5_with_datasets(tmp_path):
    """Build a small in-memory HDF5 file containing typical layouts."""
    path = tmp_path / "fixture.h5"
    with h5py.File(path, "w") as f:
        # Scalar value as a 1-element array (the common LMJ layout)
        f.create_dataset("scalar", data=np.array([42.5]))
        # Label as a 2-element string list
        f.create_dataset("label2", data=np.array([b"X-Axis", b"Y-Axis"], dtype="S20"))
        # Label as a 3-element string list
        f.create_dataset("label3", data=np.array([b"X", b"Y", b"Z"], dtype="S20"))
        # x/y pair
        f.create_dataset("xy", data=np.array([1.5, 2.5]))
    yield path


class TestProcessScalarValue:
    """Tests for process_scalar_value."""

    def test_returns_callback_result(self, h5_with_datasets):
        """The callback is applied to the dataset's first element."""
        with h5py.File(h5_with_datasets, "r") as f:
            result = process_scalar_value(f, "scalar", float)
        assert result == pytest.approx(42.5)

    def test_missing_dataset_returns_none(self, h5_with_datasets):
        """A missing dataset path yields None."""
        with h5py.File(h5_with_datasets, "r") as f:
            result = process_scalar_value(f, "missing", float)
        assert result is None


class TestProcessLabel:
    """Tests for process_label."""

    def test_two_element_label(self, h5_with_datasets):
        """A two-element label dataset fills (x, y, "")."""
        with h5py.File(h5_with_datasets, "r") as f:
            xl, yl, zl = process_label(f, "label2")
        assert xl == "X-Axis"
        assert yl == "Y-Axis"
        assert zl == ""

    def test_three_element_label(self, h5_with_datasets):
        """A three-element label dataset fills (x, y, z)."""
        with h5py.File(h5_with_datasets, "r") as f:
            xl, yl, zl = process_label(f, "label3")
        assert (xl, yl, zl) == ("X", "Y", "Z")

    def test_missing_returns_empty_strings(self, h5_with_datasets):
        """A missing label dataset returns three empty strings."""
        with h5py.File(h5_with_datasets, "r") as f:
            result = process_label(f, "missing")
        assert result == ("", "", "")


class TestProcessXyValues:
    """Tests for process_xy_values."""

    def test_returns_pair(self, h5_with_datasets):
        """A two-element dataset is returned as a (x, y) pair."""
        with h5py.File(h5_with_datasets, "r") as f:
            x, y = process_xy_values(f, "xy")
        assert x == pytest.approx(1.5)
        assert y == pytest.approx(2.5)

    def test_missing_returns_none_pair(self, h5_with_datasets):
        """A missing dataset returns (None, None)."""
        with h5py.File(h5_with_datasets, "r") as f:
            x, y = process_xy_values(f, "missing")
        assert x is None
        assert y is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
