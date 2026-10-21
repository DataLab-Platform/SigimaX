# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX selections of 1D or 2D views in HDF5 datasets

Reading a selection only reads the selected elements, so that a view of a large
multidimensional dataset (e.g. a frame of an image stack, or the spectrum of a
pixel in a spectral cube) never loads the whole dataset.
"""

from __future__ import annotations

import dataclasses
import math

import h5py
import numpy as np

__all__ = ["NDSelection", "preview_step", "read_selection"]


@dataclasses.dataclass(frozen=True)
class NDSelection:
    """Selection of a 1D or 2D view in an N-dimensional dataset

    Args:
        displayed: displayed axes, in display order: ``(axis,)`` for a 1D view,
         ``(row_axis, column_axis)`` for a 2D view (a 2D view may be transposed)
        indices: index along each axis which is not displayed, in axis order
    """

    displayed: tuple[int, ...]
    indices: tuple[int, ...] = ()

    def validate(self, shape: tuple[int, ...]) -> None:
        """Raise ValueError if the selection does not apply to an array shape

        Args:
            shape: shape of the dataset
        """
        ndim = len(shape)
        if len(self.displayed) not in (1, 2):
            raise ValueError("A selection displays one or two axes")
        if len(set(self.displayed)) != len(self.displayed) or not all(
            0 <= axis < ndim for axis in self.displayed
        ):
            raise ValueError(f"Invalid displayed axes {self.displayed} for {ndim}D")
        hidden = [axis for axis in range(ndim) if axis not in self.displayed]
        if len(self.indices) != len(hidden):
            raise ValueError(f"Expected {len(hidden)} indices, got {len(self.indices)}")
        for axis, index in zip(hidden, self.indices):
            if not 0 <= index < shape[axis]:
                raise ValueError(f"Index {index} out of range for axis {axis}")

    def as_dict(self) -> dict[str, list[int]]:
        """Return the selection as a JSON-compatible dictionary"""
        return {"displayed": list(self.displayed), "indices": list(self.indices)}


def preview_step(shape: tuple[int, ...], max_items: int) -> int:
    """Return the smallest step keeping a strided view under a number of elements

    Args:
        shape: shape of the view
        max_items: maximum number of elements of the strided view

    Returns:
        Step to apply along each axis of the view
    """
    if max_items < 1:
        raise ValueError("max_items must be positive")
    size = math.prod(shape)
    step = max(1, math.floor((size / max_items) ** (1 / max(len(shape), 1))))
    while math.prod(math.ceil(dim / step) for dim in shape) > max_items:
        step += 1
    return step


def read_selection(
    dset: h5py.Dataset, selection: NDSelection, step: int = 1
) -> np.ndarray:
    """Read the selected view of a dataset

    Args:
        dset: HDF5 dataset
        selection: selected view
        step: step along the displayed axes (to read a decimated preview)

    Returns:
        Array with one dimension per displayed axis, in display order
    """
    selection.validate(dset.shape)
    if step < 1:
        raise ValueError("step must be positive")
    hidden = iter(selection.indices)
    region = tuple(
        slice(None, None, step) if axis in selection.displayed else next(hidden)
        for axis in range(dset.ndim)
    )
    data = np.asarray(dset[region])
    order = sorted(selection.displayed)
    return data.transpose([order.index(axis) for axis in selection.displayed])
