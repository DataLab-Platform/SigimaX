# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Curve line width tests (offscreen Qt)
-------------------------------------

Tests of the curve line width: the configured width (``sig_linewidth`` option) is
not stored in signal metadata, a width chosen by the user is stored and restored,
and both are clamped to 1.0 for curves with more points than the
``sig_linewidth_perfs_threshold`` option.
"""

from __future__ import annotations

from collections.abc import Generator

import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from plotpy.items import CurveItem
from sigima.objects import create_signal

from sigimax.adapters_plotpy.converters import create_adapter_from_object
from sigimax.adapters_plotpy.objects.signal import (
    LINE_WIDTH_KEY,
    SignalObjPlotPyAdapter,
)
from sigimax.config import get_conf

pytestmark = pytest.mark.gui

#: Number of points above which line widths are clamped in these tests
THRESHOLD = 1000
#: Configured line width used by these tests
CONFIGURED = 3.0
#: Line width chosen by the user in these tests
CHOSEN = 5.0
SMALL, LARGE = THRESHOLD // 2, THRESHOLD * 5


@pytest.fixture(name="linewidth", autouse=True)
def fixture_linewidth() -> Generator[None, None, None]:
    """Set the line width options, then restore them"""
    conf = get_conf()
    options = (conf.sig_linewidth, conf.sig_linewidth_perfs_threshold)
    old_values = [option.get() for option in options]
    conf.sig_linewidth.set(CONFIGURED)
    conf.sig_linewidth_perfs_threshold.set(THRESHOLD)
    try:
        with qt_app_context(exec_loop=False):
            yield
    finally:
        for option, value in zip(options, old_values):
            option.set(value)


def _make_adapter(size: int) -> SignalObjPlotPyAdapter:
    """Return the adapter of a new signal with a given number of points"""
    x = np.linspace(0.0, 1.0, size)
    obj = create_signal(f"Signal ({size} points)", x, np.sin(2 * np.pi * 5 * x))
    return create_adapter_from_object(obj)


def _resize(adapter: SignalObjPlotPyAdapter, item: CurveItem, size: int) -> None:
    """Change the number of points of a signal and update its curve item"""
    x = np.linspace(0.0, 1.0, size)
    adapter.obj.set_xydata(x, np.cos(x))
    adapter.update_item(item)


def _choose_width(item: CurveItem, width: float) -> None:
    """Set the line width of a curve item, as done by the user"""
    item.param.line.width = width
    item.param.update_item(item)


def _save_and_reload(
    adapter: SignalObjPlotPyAdapter, item: CurveItem, cycles: int = 2
) -> CurveItem:
    """Store the curve parameters in metadata and make a new item from them, as
    done when saving and reloading a workspace, several times"""
    for _cycle in range(cycles):
        adapter.update_metadata_from_plot_item(item)
        item = adapter.make_item()
    return item


@pytest.mark.parametrize("size, drawn", [(SMALL, CONFIGURED), (LARGE, 1.0)])
def test_configured_width_not_stored(size: int, drawn: float) -> None:
    """The configured line width is applied, clamped for large curves, and not
    stored in signal metadata"""
    adapter = _make_adapter(size)
    item = adapter.make_item()
    assert item.param.line.width == drawn
    item = _save_and_reload(adapter, item)
    assert LINE_WIDTH_KEY not in adapter.obj.metadata
    assert item.param.line.width == drawn


def test_configured_width_change_after_reload() -> None:
    """A change of the configured line width applies to reloaded curves"""
    adapter = _make_adapter(SMALL)
    item = _save_and_reload(adapter, adapter.make_item())
    get_conf().sig_linewidth.set(2.0)
    assert adapter.make_item().param.line.width == 2.0
    adapter.update_item(item)
    assert item.param.line.width == 2.0


def test_chosen_width_roundtrip() -> None:
    """A line width chosen by the user is stored and restored"""
    adapter = _make_adapter(SMALL)
    item = adapter.make_item()
    _choose_width(item, CHOSEN)
    item = _save_and_reload(adapter, item)
    assert adapter.obj.metadata[LINE_WIDTH_KEY] == CHOSEN
    assert item.param.line.width == CHOSEN


def test_chosen_width_clamped() -> None:
    """A line width chosen by the user is clamped for large curves, but stays
    stored, and is drawn again when the curve becomes small"""
    adapter = _make_adapter(SMALL)
    item = adapter.make_item()
    _choose_width(item, CHOSEN)
    adapter.update_metadata_from_plot_item(item)
    _resize(adapter, item, LARGE)
    assert item.param.line.width == 1.0
    item = _save_and_reload(adapter, item)
    assert item.param.line.width == 1.0
    assert adapter.obj.metadata[LINE_WIDTH_KEY] == CHOSEN
    _resize(adapter, item, SMALL)
    assert item.param.line.width == CHOSEN


def test_chosen_width_on_large_curve() -> None:
    """A line width chosen by the user on a large curve is stored, and drawn
    clamped"""
    adapter = _make_adapter(LARGE)
    item = adapter.make_item()
    _choose_width(item, CHOSEN)
    item = _save_and_reload(adapter, item)
    assert adapter.obj.metadata[LINE_WIDTH_KEY] == CHOSEN
    assert item.param.line.width == 1.0


def test_configured_width_chosen_again() -> None:
    """Choosing the configured line width again restores the automatic width"""
    adapter = _make_adapter(SMALL)
    item = adapter.make_item()
    _choose_width(item, CHOSEN)
    item = _save_and_reload(adapter, item)
    _choose_width(item, CONFIGURED)
    item = _save_and_reload(adapter, item)
    assert LINE_WIDTH_KEY not in adapter.obj.metadata
    get_conf().sig_linewidth.set(2.0)
    adapter.update_item(item)
    assert item.param.line.width == 2.0


def test_stale_configured_width_not_stored() -> None:
    """A curve drawn with a former configured line width (e.g. not updated yet
    after a change of the option) does not store it as chosen by the user"""
    adapter = _make_adapter(SMALL)
    item = adapter.make_item()
    get_conf().sig_linewidth.set(2.0)
    adapter.update_metadata_from_plot_item(item)
    assert LINE_WIDTH_KEY not in adapter.obj.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
