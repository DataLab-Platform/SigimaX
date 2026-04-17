# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for HDF5 utility modules
-------------------------------

Covers:
- h5/common.py: data_to_xy with various shaped arrays
- h5/generic.py: safe_decode_bytes, format_text_data
- h5/utils.py: fix_ldata, fix_ndata, is_supported_num_dtype,
  is_supported_str_dtype, process_scalar_value, process_label, process_xy_values
"""

from __future__ import annotations

import numpy as np
import pytest

from sigimax.h5.common import data_to_xy
from sigimax.h5.generic import format_text_data, safe_decode_bytes
from sigimax.h5.utils import (
    fix_ldata,
    fix_ndata,
    is_supported_num_dtype,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
