# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX views of multidimensional HDF5 datasets

Datasets with three dimensions or more (image stacks, spectral cubes...) are
imported through a view (:class:`~sigimax.h5.selection.NDView`): one signal or
image per frame. Nodes of such datasets derive from :class:`NDViewMixin`: a
default view is proposed (and previewed), and the node is imported once its view
is enabled (:meth:`NDViewMixin.set_view`). When importing, each enabled node is
replaced by one :class:`FrameNode` per frame (:func:`expand_views`), so that
applications import frames as they import other nodes; :func:`count_frames`
counts them without creating them (e.g. to confirm a large import first).
"""

from __future__ import annotations

import math

from sigimax.h5 import common
from sigimax.h5.selection import NDSelection, NDView, default_view, preview_step

__all__ = [
    "FrameNode",
    "NDViewMixin",
    "count_frames",
    "expand_views",
    "frame_index_text",
]


def frame_index_text(selection: NDSelection, ndim: int) -> str:
    """Return the indices of a frame, NumPy style, e.g. ``[3, :, :]``

    Args:
        selection: frame selection
        ndim: number of dimensions of the dataset
    """
    hidden = iter(selection.indices)
    words = [
        ":" if axis in selection.displayed else str(next(hidden))
        for axis in range(ndim)
    ]
    return "[" + ", ".join(words) + "]"


class NDViewMixin:
    """Mixin of the nodes of multidimensional datasets, imported through a view

    Subclasses call :meth:`init_view` once their shape is known, and implement
    :attr:`nd_shape` and :meth:`create_view_object`.

    Attributes:
        view: current view (None if the dataset cannot be viewed)
        import_view: True if the frames of the view are to be imported
    """

    view: NDView | None = None
    import_view: bool = False

    @property
    def nd_shape(self) -> tuple[int, ...] | None:
        """Return the shape of the multidimensional data (None: no view)"""
        raise NotImplementedError

    @property
    def interpretation(self) -> str:
        """Return the NeXus interpretation of the data (empty if not given)"""
        return ""

    def init_view(self) -> None:
        """Set the default view, not enabled, for data of three dimensions or
        more"""
        shape = self.nd_shape
        self.view = None
        if shape is not None and len(shape) >= 3 and math.prod(shape) > 0:
            self.view = default_view(shape, self.interpretation)
        self.import_view = False

    def set_view(self, view: NDView | None, enabled: bool = True) -> None:
        """Set the view, and whether its frames are to be imported

        Args:
            view: view (None: default view)
            enabled: True if the frames of the view are to be imported

        Raises:
            ValueError: if the node cannot be viewed, or the view does not apply to
             its shape
        """
        shape = self.nd_shape
        if shape is None or len(shape) < 3:
            raise ValueError("Only data with three dimensions or more is viewed")
        if view is None:
            view = default_view(shape, self.interpretation)
        view.validate(shape)
        self.view, self.import_view = view, enabled

    def frame_count(self) -> int:
        """Return the number of frames of the view (0 if there is no view)"""
        if self.view is None:
            return 0
        return len(self.view.frame_indices(len(self.nd_shape)))

    def frame_positions(  # pylint: disable=unused-argument
        self, selection: NDSelection
    ) -> dict[str, float]:
        """Return the coordinates of a frame along the hidden axes which have
        coordinates, by axis name (none by default)"""
        return {}

    def axis_name(self, dim: int) -> str:  # pylint: disable=unused-argument
        """Return the name of the axis of a dimension (empty if it has none)"""
        return ""

    def axis_label(self, dim: int) -> str:
        """Return a label describing a dimension: number, axis name and size"""
        name = self.axis_name(dim)
        size = self.nd_shape[dim]
        return f"{dim} ({name}, {size})" if name else f"{dim} ({size})"

    def frame_title(self, selection: NDSelection) -> str:
        """Return the title of the object of a frame: node name, frame indices and
        coordinates along the hidden axes, if any"""
        suffix = frame_index_text(selection, len(self.nd_shape))
        positions = self.frame_positions(selection)
        if positions:
            text = ", ".join(f"{name}={value:g}" for name, value in positions.items())
            suffix += f" ({text})"
        return self.make_title(suffix)

    def frame_nodes(self) -> list[FrameNode]:
        """Return one node per frame of the view"""
        if self.view is None:
            return []
        return [FrameNode(self, sel) for sel in self.view.selections(self.nd_shape)]

    def preview_view_object(self, max_items: int):
        """Return the object of the first frame of the view, read with a step if
        it has more than ``max_items`` elements"""
        selection = self.view.first_selection(self.nd_shape)
        return self.create_view_object(
            selection, self.frame_title(selection), max_items
        )

    def create_view_object(
        self, selection: NDSelection, title: str, max_items: int | None = None
    ):
        """Create the signal or image of a frame

        Args:
            selection: frame selection
            title: object title
            max_items: maximum number of elements to read (None: read the whole
             frame and record the origin of the object)
        """
        raise NotImplementedError

    @staticmethod
    def view_step(sizes: tuple[int, ...], max_items: int | None) -> int:
        """Return the step to read a frame of the given sizes"""
        if max_items is None or math.prod(sizes) <= max_items:
            return 1
        return preview_step(sizes, max_items)


class FrameNode(common.BaseNode):
    """Node of one frame of the view of a multidimensional node, created when the
    frames are imported

    Args:
        parent: multidimensional node
        selection: frame selection
    """

    def __init__(self, parent: NDViewMixin, selection: NDSelection) -> None:
        super().__init__(parent.h5file, parent.dset.name)
        self.parent = parent
        self.selection = selection
        self.metadata = dict(parent.metadata)

    @property
    def id(self):
        """Return node id, distinct from the HDF5 paths of the file"""
        return self.parent.id + frame_index_text(
            self.selection, len(self.parent.nd_shape)
        )

    @property
    def name(self):
        """Return node name"""
        return self.parent.name + frame_index_text(
            self.selection, len(self.parent.nd_shape)
        )

    @property
    def object_title(self):
        """Return the title of the object of the frame"""
        return self.parent.frame_title(self.selection)

    def is_supported(self) -> bool:
        """Frames are always imported"""
        return True

    def create_native_object(self):
        """Create the signal or image of the frame"""
        return self.parent.create_view_object(self.selection, self.object_title)

    def create_preview_object(self, max_items: int):
        """Return the frame, read with a step if it has more than ``max_items``
        elements"""
        return self.parent.create_view_object(
            self.selection, self.object_title, max_items
        )


def expand_views(nodes: list[common.BaseNode]) -> list[common.BaseNode]:
    """Return nodes to import, multidimensional nodes being replaced by their
    frames

    Args:
        nodes: nodes selected for import

    Returns:
        Nodes to import
    """
    expanded: list[common.BaseNode] = []
    for node in nodes:
        if isinstance(node, NDViewMixin) and node.import_view:
            expanded.extend(node.frame_nodes())
        elif not isinstance(node, NDViewMixin) or node.is_supported():
            expanded.append(node)
    return expanded


def count_frames(nodes: list[common.BaseNode]) -> int:
    """Return the number of frames :func:`expand_views` would give, without
    creating them

    Args:
        nodes: nodes selected for import

    Returns:
        Number of frames of the multidimensional nodes whose view is enabled
    """
    return sum(
        node.frame_count()
        for node in nodes
        if isinstance(node, NDViewMixin) and node.import_view
    )
