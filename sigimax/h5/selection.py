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

__all__ = ["NDSelection", "NDView", "default_view", "preview_step", "read_selection"]


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


@dataclasses.dataclass(frozen=True)
class NDView:
    """View of a multidimensional dataset, imported as one object per frame

    A frame is a 1D or 2D view (:class:`NDSelection`): frames are taken along one
    axis which is not displayed, from a first to a last index with a step, the
    other hidden axes being fixed.

    Args:
        displayed: displayed axes, in display order: ``(axis,)`` for signals,
         ``(row_axis, column_axis)`` for images
        indices: index along each axis which is not displayed, in axis order (for
         the frame axis: index of the first frame)
        frame_axis: axis along which frames are taken (None: a single frame)
        last: index of the last frame along the frame axis (included)
        step: step between frames
    """

    displayed: tuple[int, ...]
    indices: tuple[int, ...] = ()
    frame_axis: int | None = None
    last: int = 0
    step: int = 1

    def hidden_axes(self, ndim: int) -> list[int]:
        """Return the axes which are not displayed, in axis order"""
        return [axis for axis in range(ndim) if axis not in self.displayed]

    def frame_indices(self, ndim: int) -> range:
        """Return the indices of the frames along the frame axis"""
        if self.frame_axis is None:
            return range(1)
        first = self.indices[self.hidden_axes(ndim).index(self.frame_axis)]
        return range(first, self.last + 1, self.step)

    def validate(self, shape: tuple[int, ...]) -> None:
        """Raise ValueError if the view does not apply to an array shape

        Args:
            shape: shape of the dataset
        """
        ndim = len(shape)
        NDSelection(self.displayed, self.indices).validate(shape)
        if self.frame_axis is None:
            return
        if self.frame_axis not in self.hidden_axes(ndim):
            raise ValueError(f"Frame axis {self.frame_axis} is displayed or missing")
        if self.step < 1:
            raise ValueError("The step between frames must be positive")
        first = self.indices[self.hidden_axes(ndim).index(self.frame_axis)]
        if not first <= self.last < shape[self.frame_axis]:
            raise ValueError(
                f"Last frame {self.last} out of range [{first}, "
                f"{shape[self.frame_axis] - 1}]"
            )

    def selections(self, shape: tuple[int, ...]) -> list[NDSelection]:
        """Return the selection of each frame

        Args:
            shape: shape of the dataset

        Raises:
            ValueError: if the view does not apply to the shape
        """
        self.validate(shape)
        if self.frame_axis is None:
            return [NDSelection(self.displayed, self.indices)]
        position = self.hidden_axes(len(shape)).index(self.frame_axis)
        selections = []
        for index in self.frame_indices(len(shape)):
            indices = list(self.indices)
            indices[position] = index
            selections.append(NDSelection(self.displayed, tuple(indices)))
        return selections

    def as_dict(self) -> dict[str, object]:
        """Return the view as a JSON-compatible dictionary"""
        result: dict[str, object] = {
            "displayed": list(self.displayed),
            "indices": list(self.indices),
        }
        if self.frame_axis is not None:
            result.update(frame_axis=self.frame_axis, last=self.last, step=self.step)
        return result


def default_view(shape: tuple[int, ...], interpretation: str = "") -> NDView:
    """Return the default view of a multidimensional dataset: every frame along the
    axis preceding the displayed ones

    Args:
        shape: shape of the dataset (two dimensions or more)
        interpretation: NeXus ``interpretation`` of the data: ``"spectrum"``
         displays the last axis as signals, ``"rgba-image"`` displays the first
         two axes as images, one per channel (last axis); otherwise the last two
         axes are displayed as images

    Raises:
        ValueError: if the dataset has less than two dimensions
    """
    ndim = len(shape)
    if ndim < 2:
        raise ValueError("A view needs a dataset with two dimensions or more")
    if interpretation == "spectrum":
        displayed, frame_axis = (ndim - 1,), ndim - 2
    elif interpretation == "rgba-image" and ndim >= 3:
        displayed, frame_axis = (ndim - 3, ndim - 2), ndim - 1
    elif ndim == 2:
        return NDView((0, 1))
    else:
        displayed, frame_axis = (ndim - 2, ndim - 1), ndim - 3
    indices = tuple(0 for axis in range(ndim) if axis not in displayed)
    return NDView(displayed, indices, frame_axis, shape[frame_axis] - 1)


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

    def view_size(step: int) -> int:
        """Return the number of elements of the view read with step"""
        return math.prod(math.ceil(dim / step) for dim in shape)

    # The view size decreases with the step: bisect for the smallest step (with
    # one element per axis at the largest dimension, the view fits)
    low, high = 1, max((1, *shape))
    while low < high:
        middle = (low + high) // 2
        if view_size(middle) > max_items:
            low = middle + 1
        else:
            high = middle
    return low


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
