# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
PlotPy Adapter Signal Module
----------------------------
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

import itertools
import weakref
from contextlib import contextmanager
from typing import Generator

import numpy as np
from guidata.dataset import restore_dataset, update_dataset
from plotpy.builder import make
from plotpy.items import CurveItem, ErrorBarCurveItem
from qtpy import QtGui as QG
from sigima.objects import SignalObj

from sigimax.adapters_plotpy.objects.base import (
    BaseObjPlotPyAdapter,
)
from sigimax.config import get_conf

#: Signal metadata keys storing the curve color and line style
LINE_STYLE_KEYS = ("color", "style")


def _normalize_color(color: str) -> str:
    """Return a color as a lower-case ``#rrggbb`` string"""
    return QG.QColor(color).name()


class CurveStyles:
    """Object to manage curve styles

    Curves are given an *automatic* style, cycling through :py:attr:`COLORS` with
    each line style of :py:attr:`LINESTYLES`. Automatic styles are not stored in
    signal metadata: only a color or a line style chosen by the user is stored,
    and is then restored instead of the automatic style.
    """

    #: Curve colors: contrast ratio of at least 3:1 against both the light (white)
    #: and the dark (#222222) plot backgrounds, and hues as distinct as possible,
    #: also for deuteranopia (none of them belongs to :py:attr:`LEGACY_COLORS`)
    COLORS = (
        "#2a77ae",  # blue
        "#d47900",  # orange
        "#23814c",  # green
        "#df324f",  # red
        "#8a7aca",  # lavender
        "#8a6c07",  # ochre
        "#c42da4",  # magenta
        "#149a98",  # teal
        "#759105",  # olive
        "#b88272",  # rosewood
    )
    #: Curve line styles (dotted styles are hard to read with thin lines)
    LINESTYLES = ("SolidLine", "DashLine")
    #: Colors of the automatic style cycle of SigimaX 1.0 and DataLab 1.3 or earlier
    LEGACY_COLORS = (
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    )
    #: Line styles of the automatic style cycle of SigimaX 1.0 and DataLab 1.3 or
    #: earlier
    LEGACY_LINESTYLES = ("SolidLine", "DashLine", "DashDotLine", "DashDotDotLine")

    def __init__(self) -> None:
        self.__suspend = False
        self.curve_style = self.style_generator()
        self.__automatic: weakref.WeakKeyDictionary[CurveItem, tuple[str, str]] = (
            weakref.WeakKeyDictionary()
        )

    @staticmethod
    def style_at(index: int) -> tuple[str, str]:
        """Return the automatic style at a given position of the cycle

        Args:
            index: position in the style cycle (0 for the first curve)

        Returns:
            Tuple (color, line style)
        """
        ncolors = len(CurveStyles.COLORS)
        color = CurveStyles.COLORS[index % ncolors]
        linestyle = CurveStyles.LINESTYLES[
            (index // ncolors) % len(CurveStyles.LINESTYLES)
        ]
        return color, linestyle

    @staticmethod
    def style_generator() -> Generator[tuple[str, str], None, None]:
        """Cycling through curve styles"""
        for index in itertools.count():
            yield CurveStyles.style_at(index)

    @staticmethod
    def is_legacy_automatic(color: str | None, linestyle: str | None) -> bool:
        """Return True if a stored style may come from the automatic style cycle of
        earlier versions, which stored automatic styles in signal metadata

        Signal metadata are not converted when curves are displayed: a stored color
        and line style are always restored, whatever their values. Applications
        may use this method to convert, when loading them, data saved by earlier
        versions (e.g. by removing such styles from the signal metadata, so that
        curves are given the current automatic styles).

        Args:
            color: stored color (None if not stored)
            linestyle: stored line style (None if not stored)

        Returns:
            True if both the color and the line style are stored and belong to the
            automatic style cycle of earlier versions
        """
        if not isinstance(color, str) or not isinstance(linestyle, str):
            return False
        return (
            _normalize_color(color) in CurveStyles.LEGACY_COLORS
            and linestyle in CurveStyles.LEGACY_LINESTYLES
        )

    def apply_style(
        self, item: CurveItem, update_from: CurveItem | None = None
    ) -> None:
        """Apply automatic style to curve

        Args:
            item: curve item
            update_from: curve item replaced by ``item``, if any: its automatic
             style is kept, instead of taking the next style of the cycle
        """
        automatic = None if update_from is None else self.__automatic.get(update_from)
        if automatic is not None:
            color, linestyle = automatic
        elif self.__suspend:
            # Suspend mode: always apply the first style
            color, linestyle = self.style_at(0)
        else:
            color, linestyle = next(self.curve_style)
        self.set_automatic_style(item, color, linestyle)
        item.param.symbol.marker = "NoSymbol"
        # Note: line width is set separately via apply_line_width()
        # to ensure it's always recalculated based on current data size and settings

    def set_automatic_style(self, item: CurveItem, color: str, linestyle: str) -> None:
        """Set the automatic style of a curve and apply it to the curve parameters

        The plot item itself is not updated: call ``item.param.update_item(item)``
        to update it.

        Args:
            item: curve item
            color: curve color
            linestyle: curve line style
        """
        color = _normalize_color(color)
        item.param.line.color = color
        item.param.line.style = linestyle
        self.__automatic[item] = (color, linestyle)

    def get_automatic_style(self, item: CurveItem) -> tuple[str, str] | None:
        """Return the automatic style of a curve

        Args:
            item: curve item

        Returns:
            Tuple (color, line style), or None if the curve was not given an
            automatic style
        """
        return self.__automatic.get(item)

    def has_automatic_style(self, item: CurveItem) -> bool:
        """Return True if a curve is shown with its automatic style, i.e. if its
        color and line style were not chosen by the user

        Args:
            item: curve item

        Returns:
            True if the curve is shown with its automatic style
        """
        automatic = self.__automatic.get(item)
        line = item.param.line
        return automatic is not None and automatic == (
            _normalize_color(line.color),
            line.style,
        )

    def restore_automatic_style(self, item: CurveItem) -> None:
        """Restore the automatic style of a curve (curve parameters only)

        Args:
            item: curve item
        """
        automatic = self.__automatic.get(item)
        if automatic is not None:
            self.set_automatic_style(item, *automatic)

    def reset_styles(self) -> None:
        """Reset styles"""
        self.curve_style = self.style_generator()

    @contextmanager
    def alternative(
        self, other_style_generator: Generator[tuple[str, str], None, None]
    ) -> Generator[None, None, None]:
        """Use an alternative style generator"""
        old_style_generator = self.curve_style
        self.curve_style = other_style_generator
        try:
            yield
        finally:
            self.curve_style = old_style_generator

    @contextmanager
    def suspend(self) -> Generator[None, None, None]:
        """Suspend style generator: curves are given the first style of the cycle,
        without using the next style of the cycle"""
        old_suspend = self.__suspend
        self.__suspend = True
        try:
            yield
        finally:
            self.__suspend = old_suspend


CURVESTYLES = CurveStyles()  # This is the unique instance of the CurveStyles class


def apply_line_width(item: CurveItem) -> None:
    """Apply line width to curve item with smart clamping for large datasets

    Args:
        item: curve item
    """
    # Get data size
    data_size = item.get_data()[0].size

    # Get configured line width
    line_width = get_conf().sig_linewidth.get()

    # For large datasets, clamp linewidth to 1.0 for performance
    # (thick lines cause ~10x rendering slowdown due to Qt raster engine)
    threshold = get_conf().sig_linewidth_perfs_threshold.get()
    if data_size > threshold and line_width > 1.0:
        line_width = 1.0

    # Apply the line width
    item.param.line.width = line_width


def apply_downsampling(item: CurveItem, do_not_update: bool = False) -> None:
    """Apply automatic downsampling to curve item

    When the ``sig_autodownsampling`` option is enabled, a curve with more points
    than the ``sig_autodownsampling_maxpoints`` option is downsampled for display,
    with the smallest factor drawing at most this number of points. The data of
    the curve are not modified.

    Args:
        item: curve item
        do_not_update: if True, do not update the item even if the downsampling
         parameters have changed
    """
    param = item.param
    old_state = (param.use_dsamp, param.dsamp_factor)
    param.use_dsamp = False
    if get_conf().sig_autodownsampling.get():
        nbpoints = item.get_data()[0].size
        maxpoints = get_conf().sig_autodownsampling_maxpoints.get()
        if nbpoints > maxpoints:
            param.use_dsamp = True
            param.dsamp_factor = -(-nbpoints // maxpoints)  # Rounded up
    new_state = (param.use_dsamp, param.dsamp_factor)
    if not do_not_update and old_state != new_state:
        item.update_data()


class SignalObjPlotPyAdapter(BaseObjPlotPyAdapter[SignalObj, CurveItem]):
    """Signal object plot item adapter class"""

    DEFAULT_FMT = "g"
    # conf_format is inherited from the base adapter (returns get_conf().sig_format)

    def update_plot_item_parameters(self, item: CurveItem) -> None:
        """Update plot item parameters from object data/metadata

        Takes into account a subset of plot item parameters. Those parameters may
        have been overriden by object metadata entries or other object data. The goal
        is to update the plot item accordingly.

        A color or a line style stored in the signal metadata is always restored:
        it has been chosen by the user (automatic styles are not stored).

        This is *almost* the inverse operation of `update_metadata_from_plot_item`.

        Args:
            item: plot item
        """
        update_dataset(item.param.line, self.obj.metadata)
        update_dataset(item.param.symbol, self.obj.metadata)
        super().update_plot_item_parameters(item)

    def update_metadata_from_plot_item(self, item: CurveItem) -> None:
        """Update metadata from plot item.

        Takes into account a subset of plot item parameters. Those parameters may
        have been modified by the user through the plot item GUI. The goal is to
        update the metadata accordingly.

        The color and the line style are stored only if they were chosen by the
        user, i.e. if they differ from the automatic style of the curve.

        This is *almost* the inverse operation of `update_plot_item_parameters`.

        Args:
            item: plot item
        """
        super().update_metadata_from_plot_item(item)
        restore_dataset(item.param.line, self.obj.metadata)
        restore_dataset(item.param.symbol, self.obj.metadata)
        if CURVESTYLES.has_automatic_style(item):
            for key in LINE_STYLE_KEYS:
                self.obj.metadata.pop(key, None)

    def make_item(self, update_from: CurveItem | None = None) -> CurveItem:
        """Make plot item from data.

        Args:
            update_from: plot item to update from

        Returns:
            Plot item
        """
        o = self.obj
        if len(o.xydata) in (2, 4):
            assert isinstance(o.xydata, np.ndarray)
            if len(o.xydata) == 2:  # x, y signal
                x, y = o.xydata
                item = make.mcurve(x.real, y.real, label=o.title)
            else:  # x, y, dx, dy error bar signal
                x, y, dx, dy = o.xydata
                if o.dx is None and o.dy is None:  # x, y signal with no error
                    item = make.mcurve(x.real, y.real, label=o.title)
                elif o.dx is None:  # x, y, dy error bar signal with y error
                    item = make.merror(x.real, y.real, dy.real, label=o.title)
                else:  # x, y, dx, dy error bar signal with x error
                    dy = np.zeros_like(y) if dy is None else dy
                    item = make.merror(x.real, y.real, dx.real, dy.real, label=o.title)
            # Apply style (without linewidth, will be set separately)
            CURVESTYLES.apply_style(item, update_from=update_from)
            apply_downsampling(item, do_not_update=True)
            # Apply linewidth with smart clamping based on actual data size
            apply_line_width(item)
        else:
            raise RuntimeError("data not supported")
        if update_from is None:
            self.update_plot_item_parameters(item)
        else:
            update_dataset(item.param, update_from.param)
            item.update_params()
        return item

    def update_item(self, item: CurveItem, data_changed: bool = True) -> None:
        """Update plot item from data.

        Args:
            item: plot item
            data_changed: if True, data has changed
        """
        o = self.obj
        if data_changed:
            assert isinstance(o.xydata, np.ndarray)
            if len(o.xydata) == 2:  # x, y signal
                x, y = o.xydata
                assert isinstance(x, np.ndarray) and isinstance(y, np.ndarray)
                item.set_data(x.real, y.real)
            elif len(o.xydata) == 3:  # x, y, dy error bar signal
                x, y, dy = o.xydata
                assert (
                    isinstance(x, np.ndarray)
                    and isinstance(y, np.ndarray)
                    and isinstance(dy, np.ndarray)
                )
                item.set_data(x.real, y.real, dy=dy.real)
            elif len(o.xydata) == 4:  # x, y, dx, dy error bar signal
                x, y, dx, dy = o.xydata
                assert (
                    isinstance(x, np.ndarray)
                    and isinstance(y, np.ndarray)
                    and isinstance(dx, np.ndarray)
                    and isinstance(dy, np.ndarray)
                )
                if isinstance(item, ErrorBarCurveItem):
                    item.set_data(x.real, y.real, dx.real, dy.real)
                else:
                    # xydata has 4 rows but dx/dy are all NaN (no real
                    # error bars) — the plot item is a plain CurveItem
                    item.set_data(x.real, y.real)
        item.param.label = o.title
        apply_downsampling(item)
        # Reapply linewidth with smart clamping (data size may have changed)
        apply_line_width(item)
        self.update_plot_item_parameters(item)

    def add_label_with_title(self, title: str | None = None) -> None:
        """Add label with title annotation

        Args:
            title: title (if None, use signal title)
        """
        title = self.obj.title if title is None else title
        if title:
            label = make.label(title, "TL", (0, 0), "TL")
            self.add_annotations_from_items([label])
