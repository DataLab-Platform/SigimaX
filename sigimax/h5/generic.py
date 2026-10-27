# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX Generic HDF5 format support
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

import functools
import math

import h5py
import numpy as np
from guidata.utils.misc import to_string
from sigima.io.common.converters import convert_array_to_valid_dtype
from sigima.objects import (
    ImageObj,
    SignalObj,
    create_image,
    create_signal,
    make_experimental_source,
    set_experimental_source,
)

from sigimax.h5 import common, utils
from sigimax.h5.selection import NDSelection, preview_step, read_selection
from sigimax.h5.views import NDViewMixin

#: Maximum number of elements read to show the textual preview of an array
TEXT_PREVIEW_MAX_ITEMS = 100

#: Number of compound records read to decide if their string fields matter
COMPOUND_SAMPLE_SIZE = 1000


def _unavailable_filters_text(missing: list[str]) -> str:
    """Return the text of a dataset that cannot be read for want of filters"""
    return "<compressed with unavailable filter: " + ", ".join(missing) + ">"


# =============================================================================
# Encoding and Data Reading Utilities
# =============================================================================


def safe_decode_bytes(data, fallback="<binary data>"):
    """Safely decode bytes to string using multiple encoding strategies."""
    if isinstance(data, str):
        return data
    if not isinstance(data, bytes):
        return str(data)

    # Try encodings in order of preference
    for encoding in ["utf-8", "latin1", "cp1252", "iso-8859-1", "ascii"]:
        try:
            decoded = data.decode(encoding)
            # For legacy encodings, validate the result looks reasonable
            if encoding in ["latin1", "cp1252", "iso-8859-1"]:
                if _is_reasonable_text(decoded):
                    return decoded
            else:
                return decoded
        except (UnicodeDecodeError, UnicodeError):
            continue

    # Final fallback with replacement characters
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:  # pylint: disable=broad-except
        return fallback


def _is_reasonable_text(text):
    """Check if decoded text looks reasonable (mostly printable)."""
    if not text:
        return True

    printable_chars = sum(1 for c in text if c.isprintable() or c.isspace())
    ratio = printable_chars / len(text)

    # Accept if mostly printable or short enough to be likely text
    return ratio >= 0.8 or len(text) < 20


def safe_read_dataset(dset, fallback_data=None):
    """Safely read HDF5 dataset with encoding error handling."""
    try:
        return dset[()]
    except UnicodeDecodeError:
        # Try alternative reading strategies for problematic encodings
        return _try_alternative_read(dset, fallback_data)
    except (TypeError, ValueError, OSError):
        return fallback_data


def _try_alternative_read(dset, fallback_data):
    """Try alternative strategies to read datasets with encoding issues."""
    strategies = [
        lambda d: d.asstr()[()],  # Try string conversion
        lambda d: d.astype("S")[()],  # Try reading as bytes
    ]

    for strategy in strategies:
        try:
            return strategy(dset)
        except Exception:  # pylint: disable=broad-except
            continue

    return fallback_data


# =============================================================================
# Text Formatting Utilities
# =============================================================================


def format_text_data(data):
    """Format various types of data for text display."""
    if data is None:
        return "<unreadable data>"

    try:
        return to_string(data)
    except (UnicodeDecodeError, UnicodeError):
        return _handle_encoding_issues(data)


def _handle_encoding_issues(data):
    """Handle data with encoding issues."""
    if isinstance(data, bytes):
        return safe_decode_bytes(data)

    if isinstance(data, np.ndarray):
        if data.dtype.kind in ["S", "a", "U"]:  # String arrays
            return _format_string_array(data)
        if data.dtype.names:  # Compound data
            return _format_compound_data(data)

    return f"<data with encoding issues: {type(data)}>"


def _format_string_array(data):
    """Format string arrays with encoding handling."""
    try:
        if data.size == 1:
            return safe_decode_bytes(data.item())
        # Show first few elements
        items = []
        for i, item in enumerate(data.flat):
            if i >= 5:
                items.append("...")
                break
            items.append(safe_decode_bytes(item))
        return f"[{', '.join(items)}]"
    except Exception:  # pylint: disable=broad-except
        return f"<string array: {data.shape} {data.dtype}>"


def _format_compound_data(data):
    """Format compound data with encoding handling."""
    try:
        result_parts = []
        for field_name in data.dtype.names:
            field_data = data[field_name]
            if hasattr(field_data, "item"):
                field_data = field_data.item()

            if isinstance(field_data, bytes):
                field_value = safe_decode_bytes(field_data)
            else:
                field_value = str(field_data)

            result_parts.append(f"{field_name}: {field_value}")

        return f"({', '.join(result_parts)})"
    except Exception:  # pylint: disable=broad-except
        return f"<compound data: {data.dtype}>"


# =============================================================================
# Base Node Class
# =============================================================================


class BaseGenericNode(common.BaseNode):
    """Base class for generic HDF5 data nodes with encoding support."""

    @classmethod
    def match(cls, dset):
        """Return True if h5 dataset matches this node pattern."""
        return isinstance(dset, h5py.Dataset)

    @functools.cached_property
    def missing_filters(self) -> list[str]:
        """Compression filters of the dataset that HDF5 cannot apply (see
        :func:`sigimax.h5.utils.unavailable_filters`)"""
        return utils.unavailable_filters(self.dset)

    @property
    def icon_name(self):
        """Icon name associated to node."""
        return "h5scalar.svg"

    @property
    def data(self):
        """Data associated to node, if available."""
        return safe_read_dataset(self.dset, fallback_data=None)

    @property
    def dtype_str(self):
        """Return string representation of node data type."""
        try:
            return str(self.dset.dtype)
        except (UnicodeDecodeError, TypeError, ValueError):
            if self.data is None:
                return "unknown"
            try:
                return str(self.data.dtype)
            except Exception:  # pylint: disable=broad-except
                return "unknown"

    @property
    def text(self):
        """Return node textual representation."""
        return format_text_data(self.data)


# =============================================================================
# Specialized Node Classes
# =============================================================================


class GenericScalarNode(BaseGenericNode):
    """Node for scalar HDF5 data."""

    @classmethod
    def match(cls, dset):
        """Match scalar numeric data."""
        return (
            super().match(dset)
            and dset.shape == ()
            and utils.is_supported_num_dtype(dset)
        )


class GenericTextNode(BaseGenericNode):
    """Node for text/string HDF5 data."""

    @classmethod
    def match(cls, dset):
        """Match scalar text or string data."""
        return (
            super().match(dset)
            and dset.shape == ()
            and utils.is_string_dtype(dset.dtype)
        )

    @property
    def dtype_str(self):
        """Return simplified dtype for text data."""
        return "string"

    @property
    def text(self):
        """Return formatted text with special handling for single arrays."""
        if self.data is None:
            return "<unreadable data>"

        try:
            if utils.is_single_str_array(self.data):
                item = self.data[0]
                return safe_decode_bytes(item) if isinstance(item, bytes) else str(item)
            return format_text_data(self.data)
        except (UnicodeDecodeError, UnicodeError):
            return _handle_text_encoding_issues(self.data)


def _handle_text_encoding_issues(data):
    """Handle encoding issues specific to text nodes."""
    if isinstance(data, bytes):
        return safe_decode_bytes(data)
    if isinstance(data, np.ndarray) and data.dtype.kind in ["S", "a"]:
        try:
            if data.size == 1:
                return safe_decode_bytes(data.item())
            decoded = [safe_decode_bytes(item) for item in data.flat]
            return str(decoded[:10])  # Show first 10 elements
        except Exception:  # pylint: disable=broad-except
            return f"<string data: {data.shape}>"
    return "<text with encoding issues>"


class GenericArrayNode(BaseGenericNode):
    """Node for array HDF5 data, including numeric arrays from compound data."""

    IS_ARRAY = True

    def __init__(self, h5file, dname):
        super().__init__(h5file, dname)
        self.__layout: tuple[tuple[int, ...], np.dtype] | None = None

    @classmethod
    def match(cls, dset):
        """Match numeric array data, including convertible compound data."""
        return super().match(dset) and cls.numeric_layout(dset) is not None

    @classmethod
    def numeric_layout(cls, dset) -> tuple[tuple[int, ...], np.dtype] | None:
        """Return shape and dtype of the numeric array read from a dataset.

        Only the dataset metadata is used, except for compound datasets mixing
        numeric and string fields: their first records are read to check whether
        the string fields carry information that a numeric array would lose.

        Args:
            dset: HDF5 dataset

        Returns:
            Shape and dtype of the 1D or 2D numeric array, or None if the dataset
            does not provide one
        """
        dtype, shape = dset.dtype, dset.shape
        if not shape:
            return None
        if dtype.names is not None:
            return cls._compound_layout(dset)
        if utils.is_supported_num_dtype(dset) and len(shape) in (1, 2):
            return shape, dtype
        return None

    @classmethod
    def _compound_layout(cls, dset) -> tuple[tuple[int, ...], np.dtype] | None:
        """Return shape and dtype of the numeric array read from a compound
        dataset (see :meth:`numeric_layout`).

        Args:
            dset: HDF5 compound dataset

        Returns:
            Shape and dtype of the 1D or 2D numeric array, or None if the dataset
            does not provide one
        """
        dtype, shape = dset.dtype, dset.shape
        fields = {name: dtype.fields[name][0] for name in dtype.names}
        numeric = [
            name for name, fdt in fields.items() if np.issubdtype(fdt, np.number)
        ]
        if not numeric:
            return None
        if len(numeric) != len(fields):
            sample, _truncated = utils.read_bounded(dset, COMPOUND_SAMPLE_SIZE)
            for name in fields:
                if name not in numeric and cls._has_meaningful_string_data(
                    sample[name]
                ):
                    return None
        if len(numeric) == 1:
            new_dtype = fields[numeric[0]]
        else:
            new_dtype = np.result_type(*(fields[name] for name in numeric))
            shape = shape + (len(numeric),)
        if not new_dtype.name.startswith(("int", "uint", "float", "complex")):
            return None
        return (shape, new_dtype) if len(shape) in (1, 2) else None

    @classmethod
    def extract_numeric_from_compound(cls, data):
        """Extract a numeric array from compound data."""
        if not (hasattr(data.dtype, "names") and data.dtype.names):
            return None

        # Find ALL fields and check if they are numeric
        all_fields = list(data.dtype.names)
        numeric_fields = []
        for field_name in all_fields:
            field_dtype = data.dtype.fields[field_name][0]
            if np.issubdtype(field_dtype, np.number):
                numeric_fields.append(field_name)

        # Only convert if ALL fields are numeric (preserve all information)
        # or if there's a single numeric field and no important string data
        if len(numeric_fields) == 0:
            return None

        if len(numeric_fields) != len(all_fields):
            # Mixed data - check if non-numeric fields contain meaningful data
            for field_name in all_fields:
                if field_name not in numeric_fields:
                    field_data = data[field_name]
                    # If there's meaningful string data, don't convert
                    if cls._has_meaningful_string_data(field_data):
                        return None

        try:
            # If single numeric field, extract it directly
            if len(numeric_fields) == 1:
                return data[numeric_fields[0]]

            # Multiple numeric fields: stack them if compatible shapes
            field_data = [data[field] for field in numeric_fields]

            # Check if all fields have the same shape
            shapes = [arr.shape for arr in field_data]
            if len(set(shapes)) == 1:
                # Stack along new axis to create 2D array
                return np.stack(field_data, axis=-1)

        except Exception:  # pylint: disable=broad-except
            pass
        return None

    @classmethod
    def _has_meaningful_string_data(cls, field_data):
        """Check if string field contains meaningful data worth preserving."""
        try:
            if hasattr(field_data, "flat"):
                # Check if most entries are non-empty and meaningful
                non_empty_count = 0
                for item in field_data.flat:
                    if isinstance(item, bytes):
                        decoded = item.decode("utf-8", errors="ignore").strip()
                        if decoded and len(decoded) > 0:
                            non_empty_count += 1
                    elif isinstance(item, str) and item.strip():
                        non_empty_count += 1

                # If most entries have meaningful content, preserve it
                return non_empty_count / field_data.size > 0.5
            return True  # Default to preserving unknown string data
        except Exception:  # pylint: disable=broad-except
            return True  # Conservative: preserve if we can't determine

    @property
    def data(self):
        """Data associated to node, if available."""
        raw_data = safe_read_dataset(self.dset, fallback_data=None)

        # If this is compound data, try to extract numeric array
        if (
            raw_data is not None
            and isinstance(raw_data, np.ndarray)
            and hasattr(raw_data.dtype, "names")
            and raw_data.dtype.names is not None
        ):
            numeric_data = self.extract_numeric_from_compound(raw_data)
            if numeric_data is not None:
                return numeric_data

        return raw_data

    @property
    def layout(self) -> tuple[tuple[int, ...], np.dtype]:
        """Shape and dtype of the numeric array associated to node"""
        if self.__layout is None:
            self.__layout = self.numeric_layout(self.dset)
        return self.__layout

    def is_supported(self) -> bool:
        """Return True if node is associated to supported data"""
        return int(np.prod(self.layout[0])) > 1 and not self.missing_filters

    @property
    def __is_signal(self):
        """Return True if array represents a signal"""
        shape = self.layout[0]
        return len(shape) == 1 or shape[0] in (1, 2) or shape[1] in (1, 2)

    @property
    def icon_name(self):
        """Icon name associated to node"""
        if self.is_supported():
            return "signal.svg" if self.__is_signal else "image.svg"
        return "h5array.svg"

    @property
    def shape_str(self):
        """Return string representation of node shape, if any"""
        return " x ".join([str(size) for size in self.layout[0]])

    @property
    def dtype_str(self):
        """Return string representation of node data type, if any"""
        return str(self.layout[1])

    @property
    def text(self):
        """Return node textual representation"""
        if self.missing_filters:
            return _unavailable_filters_text(self.missing_filters)
        data, truncated = utils.read_bounded(self.dset, TEXT_PREVIEW_MAX_ITEMS)
        if self.dset.dtype.names is not None:
            data = self.extract_numeric_from_compound(data)
        return str(data) + (" ..." if truncated else "")

    def create_native_object(self):
        """Create native object, if supported"""
        if self.__is_signal:
            obj = create_signal(self.object_title)
            try:
                self.set_signal_data(obj)
            except ValueError:
                obj = None
        else:
            obj = create_image(self.object_title)
            try:
                self.set_image_data(obj)
            except ValueError:
                obj = None
        return obj

    def create_preview_object(self, max_items: int):
        """Return the native object, or a decimated one if the dataset is larger
        than ``max_items`` (1D signals and images only)"""
        shape = self.layout[0]
        if (
            math.prod(shape) <= max_items
            or self.dset.dtype.names is not None
            or (self.__is_signal and len(shape) == 2)
        ):
            return self.get_native_object()
        step = preview_step(shape, max_items)
        data = read_selection(self.dset, NDSelection(tuple(range(len(shape)))), step)
        if len(shape) == 1:
            x = np.arange(0, shape[0], step, dtype=float)
            y = convert_array_to_valid_dtype(data, SignalObj.VALID_DTYPES)
            return create_signal(self.object_title, x, y)
        obj = create_image(
            self.object_title,
            convert_array_to_valid_dtype(data, ImageObj.VALID_DTYPES),
        )
        obj.set_uniform_coords(float(step), float(step))
        return obj


class GenericNDArrayNode(BaseGenericNode, NDViewMixin):
    """Node for numeric HDF5 datasets with three dimensions or more.

    Such datasets (image stacks, spectral cubes...) are listed and described, and
    imported through a view (:class:`~sigimax.h5.views.NDViewMixin`): one signal
    or image per frame, read with :func:`sigimax.h5.selection.read_selection`.
    """

    def __init__(self, h5file, dname):
        super().__init__(h5file, dname)
        self.init_view()

    @classmethod
    def match(cls, dset):
        """Match numeric datasets with three dimensions or more."""
        return (
            super().match(dset)
            and dset.dtype.names is None
            and dset.shape is not None
            and len(dset.shape) >= 3
            and utils.is_supported_num_dtype(dset)
        )

    @property
    def nd_shape(self) -> tuple[int, ...] | None:
        """Return the shape of the dataset (None if it cannot be read)"""
        return None if self.missing_filters else self.dset.shape

    @property
    def interpretation(self) -> str:
        """Return the NeXus interpretation of the dataset (empty if not given)"""
        return to_string(self.dset.attrs.get("interpretation", "")).strip()

    def is_supported(self) -> bool:
        """Return True if the frames of the view are to be imported"""
        return self.import_view

    def can_preview(self) -> bool:
        """Return True if the dataset can be viewed"""
        return self.view is not None

    @property
    def icon_name(self):
        """Icon name associated to node"""
        if self.import_view:
            return "image.svg" if len(self.view.displayed) == 2 else "signal.svg"
        return "h5array.svg"

    @property
    def shape_str(self):
        """Return string representation of node shape, if any"""
        return " x ".join([str(size) for size in self.dset.shape])

    @property
    def text(self):
        """Return node textual representation"""
        if self.missing_filters:
            return _unavailable_filters_text(self.missing_filters)
        data, truncated = utils.read_bounded(self.dset, TEXT_PREVIEW_MAX_ITEMS)
        return str(data) + (" ..." if truncated else "")

    def create_preview_object(self, max_items: int):
        """Return the first frame of the view, read with a step if it has more
        than ``max_items`` elements"""
        return self.preview_view_object(max_items)

    def create_view_object(
        self, selection: NDSelection, title: str, max_items: int | None = None
    ):
        """Create the signal or image of a frame, with pixel indices as
        coordinates

        Args:
            selection: frame selection
            title: object title
            max_items: maximum number of elements to read (None: read the whole
             frame and record the origin of the object)
        """
        sizes = tuple(self.dset.shape[axis] for axis in selection.displayed)
        step = self.view_step(sizes, max_items)
        data = read_selection(self.dset, selection, step)
        if len(sizes) == 1:
            x = np.arange(0, sizes[0], step, dtype=float)
            obj = create_signal(title, x, common.to_signal_data(data))
        else:
            obj = create_image(
                title, convert_array_to_valid_dtype(data, ImageObj.VALID_DTYPES)
            )
            obj.set_uniform_coords(float(step), float(step))
        if max_items is None:
            source = make_experimental_source(
                "hdf5",
                self.h5file.filename,
                entry=self.dset.name,
                selection={"view": selection.as_dict()},
            )
            set_experimental_source(obj, source)
        return obj


class GenericCompoundNode(BaseGenericNode):
    """Node for compound/structured HDF5 data that can't convert to numeric arrays."""

    IS_ARRAY = True

    @classmethod
    def match(cls, dset):
        """Match compound/structured data that cannot be converted to numeric arrays."""
        return (
            super().match(dset)
            and dset.dtype.names is not None
            and bool(dset.shape)
            and GenericArrayNode.numeric_layout(dset) is None
        )

    @property
    def dtype_str(self):
        """Return detailed compound dtype information."""
        try:
            dtype = self.dset.dtype
            if dtype.names:
                field_info = []
                for name in dtype.names:
                    field_dtype = dtype.fields[name][0]
                    field_info.append(f"{name}: {field_dtype}")
                return f"compound({', '.join(field_info)})"
            return str(dtype)
        except Exception:  # pylint: disable=broad-except
            return super().dtype_str

    @property
    def text(self):
        """Return formatted compound data."""
        try:
            data, truncated = utils.read_first_items(self.dset, 3)
        except (UnicodeDecodeError, TypeError, ValueError, OSError):
            return "<unreadable compound data>"
        try:
            if data.size == 1 and not truncated:
                return self._format_single_record(data)
            return self._format_multiple_records(data, truncated)
        except Exception:  # pylint: disable=broad-except
            return f"<compound data: {self.dset.shape} records>"

    @staticmethod
    def _format_single_record(data):
        """Format a single compound record."""
        parts = []
        for field_name in data.dtype.names:
            field_value = data[field_name].item()
            if isinstance(field_value, bytes):
                field_value = safe_decode_bytes(field_value)
            parts.append(f"{field_name}: {field_value}")
        return f"({', '.join(parts)})"

    @staticmethod
    def _format_multiple_records(data, truncated):
        """Format the first compound records."""
        records = []
        for record in data.flat:
            parts = []
            for field_name in data.dtype.names:
                field_value = record[field_name]
                if isinstance(field_value, bytes):
                    field_value = safe_decode_bytes(field_value)
                parts.append(f"{field_name}: {field_value}")
            records.append(f"({', '.join(parts)})")
        if truncated:
            records.append("...")
        return f"[{', '.join(records)}]"


# =============================================================================
# Node Registration
# =============================================================================

# Register all node types with the factory
common.NODE_FACTORY.register(GenericScalarNode, is_generic=True)
common.NODE_FACTORY.register(GenericTextNode, is_generic=True)
common.NODE_FACTORY.register(GenericArrayNode, is_generic=True)
common.NODE_FACTORY.register(GenericNDArrayNode, is_generic=True)
common.NODE_FACTORY.register(GenericCompoundNode, is_generic=True)
