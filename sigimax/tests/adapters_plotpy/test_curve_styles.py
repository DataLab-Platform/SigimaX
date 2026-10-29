# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Curve style tests (offscreen Qt)
--------------------------------

Tests of the automatic curve styles: palette readability, style cycle, plot grid
defaults and persistence of the styles in signal metadata.
"""

from __future__ import annotations

import pytest
from guidata.qthelpers import is_dark_theme, qt_app_context
from plotpy.constants import PlotType
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW
from sigima.tests.data import create_paracetamol_signal

import sigimax.config as sigimax_config
from sigimax.adapters_plotpy.converters import create_adapter_from_object
from sigimax.adapters_plotpy.objects.signal import (
    CURVESTYLES,
    LINE_STYLE_KEYS,
    CurveStyles,
    SignalObjPlotPyAdapter,
)
from sigimax.config import GRID_COLORS_DARK, GRID_COLORS_LIGHT, get_conf
from sigimax.widgets.plotdock import DockablePlotWidget

pytestmark = pytest.mark.gui

LIGHT_BG, DARK_BG = "#ffffff", "#222222"


def _luminance(color: str) -> float:
    """Return the relative luminance of a color (WCAG 2.x definition)"""
    qcolor = QG.QColor(color)

    def channel(value: float) -> float:
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (
        channel(v) for v in (qcolor.redF(), qcolor.greenF(), qcolor.blueF())
    )
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(color1: str, color2: str) -> float:
    """Return the contrast ratio between two colors (WCAG 2.x definition)"""
    lum1, lum2 = sorted((_luminance(color1), _luminance(color2)), reverse=True)
    return (lum1 + 0.05) / (lum2 + 0.05)


def _make_signal_adapter() -> SignalObjPlotPyAdapter:
    """Return the adapter of a new signal"""
    return create_adapter_from_object(create_paracetamol_signal())


def _line_style(item) -> tuple[str, str]:
    """Return the color and the line style of a curve item"""
    return QG.QColor(item.param.line.color).name(), item.param.line.style


def test_palette_readability() -> None:
    """Curve colors are readable on light and dark plot backgrounds"""
    colors = CurveStyles.COLORS
    assert len(set(colors)) == len(colors) >= 10
    for color in colors:
        assert color == QG.QColor(color).name()
        assert _contrast(color, LIGHT_BG) >= 3.0, color
        assert _contrast(color, DARK_BG) >= 3.0, color
    # Styles stored by earlier versions are recognized from these colors only:
    assert not set(colors) & set(CurveStyles.LEGACY_COLORS)


def test_style_cycle() -> None:
    """Automatic styles cycle through colors with solid lines, then dashed lines"""
    assert CurveStyles.LINESTYLES == ("SolidLine", "DashLine")
    ncolors = len(CurveStyles.COLORS)
    generator = CurveStyles.style_generator()
    styles = [next(generator) for _index in range(2 * ncolors + 1)]
    assert styles == [CurveStyles.style_at(i) for i in range(2 * ncolors + 1)]
    assert styles[:ncolors] == [(c, "SolidLine") for c in CurveStyles.COLORS]
    assert styles[ncolors : 2 * ncolors] == [
        (c, "DashLine") for c in CurveStyles.COLORS
    ]
    assert styles[2 * ncolors] == styles[0]


def test_update_from_keeps_style() -> None:
    """Making an item from an existing item keeps its style, without using a new
    style of the cycle"""
    with qt_app_context(exec_loop=False):
        CURVESTYLES.reset_styles()
        adapter = _make_signal_adapter()
        item = adapter.make_item()
        assert _line_style(item) == CurveStyles.style_at(0)
        copy = adapter.make_item(update_from=item)
        assert _line_style(copy) == CurveStyles.style_at(0)
        assert CURVESTYLES.has_automatic_style(copy)
        assert _line_style(_make_signal_adapter().make_item()) == (
            CurveStyles.style_at(1)
        )


def test_automatic_style_not_stored() -> None:
    """Automatic styles are not stored in signal metadata"""
    with qt_app_context(exec_loop=False):
        adapter = _make_signal_adapter()
        item = adapter.make_item()
        assert CURVESTYLES.has_automatic_style(item)
        adapter.update_metadata_from_plot_item(item)
        for key in LINE_STYLE_KEYS:
            assert key not in adapter.obj.metadata
        # Other line parameters are still stored
        assert "width" in adapter.obj.metadata


def test_explicit_style_roundtrip() -> None:
    """A style chosen by the user is stored and restored"""
    with qt_app_context(exec_loop=False):
        adapter = _make_signal_adapter()
        item = adapter.make_item()
        # A palette color, on a curve whose automatic color is another one:
        color = next(c for c in CurveStyles.COLORS if c != item.param.line.color)
        item.param.line.color = color
        item.param.line.style = "DotLine"
        item.param.update_item(item)
        assert not CURVESTYLES.has_automatic_style(item)
        adapter.update_metadata_from_plot_item(item)
        assert adapter.obj.metadata["color"] == color
        assert adapter.obj.metadata["style"] == "DotLine"
        item2 = adapter.make_item()
        assert _line_style(item2) == (color, "DotLine")
        assert not CURVESTYLES.has_automatic_style(item2)


@pytest.mark.parametrize("linestyle", CurveStyles.LEGACY_LINESTYLES)
def test_legacy_style_is_automatic(linestyle: str) -> None:
    """Styles stored by earlier versions from their style cycle are automatic"""
    with qt_app_context(exec_loop=False):
        adapter = _make_signal_adapter()
        adapter.obj.metadata["color"] = CurveStyles.LEGACY_COLORS[1]
        adapter.obj.metadata["style"] = linestyle
        item = adapter.make_item()
        assert CURVESTYLES.has_automatic_style(item)
        assert _line_style(item)[0] in CurveStyles.COLORS
        adapter.update_metadata_from_plot_item(item)
        for key in LINE_STYLE_KEYS:
            assert key not in adapter.obj.metadata


def test_partial_legacy_style_is_explicit() -> None:
    """A stored color without line style (e.g. set by a script) is explicit"""
    with qt_app_context(exec_loop=False):
        adapter = _make_signal_adapter()
        adapter.obj.metadata["color"] = CurveStyles.LEGACY_COLORS[1]
        item = adapter.make_item()
        assert _line_style(item)[0] == CurveStyles.LEGACY_COLORS[1]
        assert not CURVESTYLES.has_automatic_style(item)


def test_restore_automatic_style() -> None:
    """The automatic style of a curve may be restored"""
    with qt_app_context(exec_loop=False):
        adapter = _make_signal_adapter()
        item = adapter.make_item()
        automatic = CURVESTYLES.get_automatic_style(item)
        item.param.line.color = "#000000"
        assert not CURVESTYLES.has_automatic_style(item)
        CURVESTYLES.restore_automatic_style(item)
        assert CURVESTYLES.has_automatic_style(item)
        assert _line_style(item) == automatic
        CURVESTYLES.set_automatic_style(item, *CurveStyles.style_at(3))
        assert _line_style(item) == CurveStyles.style_at(3)
        assert CURVESTYLES.has_automatic_style(item)


@pytest.mark.parametrize(
    "dark, background, grid_colors",
    [(False, LIGHT_BG, GRID_COLORS_LIGHT), (True, DARK_BG, GRID_COLORS_DARK)],
)
def test_grid_defaults(
    monkeypatch: pytest.MonkeyPatch,
    dark: bool,
    background: str,
    grid_colors: tuple[str, str],
) -> None:
    """The plot grid is discreet and does not hide curves"""
    monkeypatch.setattr(sigimax_config, "is_dark_theme", lambda: dark)
    defaults = get_conf().get_plotpy_defaults()["plot"]
    major, minor = grid_colors
    assert defaults["grid/maj_line/color"] == major
    assert defaults["grid/min_line/color"] == minor
    assert defaults["grid/maj_line/style"] == "SolidLine"
    assert defaults["grid/min_line/style"] == "SolidLine"
    assert 1.2 <= _contrast(major, background) <= 1.6
    assert _contrast(minor, background) < _contrast(major, background)
    for color in CurveStyles.COLORS:
        assert _contrast(color, major) >= 2.0, color


def test_dock_grid_after_color_mode_change() -> None:
    """Plot docks use the application grid style after a color mode change"""
    with qt_app_context(exec_loop=False):
        parent = QW.QWidget()
        dock = DockablePlotWidget(parent, PlotType.CURVE)
        plot = dock.get_plot()
        # PlotPy updates the grid with its own defaults when the color mode changes:
        plot.grid.gridparam.maj_line.color = "#808080"
        plot.grid.gridparam.maj_line.style = "DotLine"
        plot.grid.gridparam.update_grid(plot.grid)
        get_conf().apply_plotpy_defaults()
        dock.update_color_mode()
        major = (GRID_COLORS_DARK if is_dark_theme() else GRID_COLORS_LIGHT)[0]
        assert plot.grid.gridparam.maj_line.color == major
        assert plot.grid.gridparam.maj_line.style == "SolidLine"
