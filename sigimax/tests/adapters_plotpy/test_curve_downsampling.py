# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Curve auto downsampling tests (offscreen Qt)
--------------------------------------------

Tests of the automatic downsampling of curves with many points, driven by the
``sig_autodownsampling`` and ``sig_autodownsampling_maxpoints`` options.
"""

from __future__ import annotations

import math
from collections.abc import Generator

import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from plotpy.items import CurveItem
from sigima.objects import create_signal

from sigimax.adapters_plotpy.converters import create_adapter_from_object
from sigimax.adapters_plotpy.objects.signal import (
    SignalObjPlotPyAdapter,
    apply_downsampling,
)
from sigimax.config import get_conf

pytestmark = pytest.mark.gui

#: Maximum number of points used by the tests (even, see `_check_downsampling`)
MAXPOINTS = 1000


@pytest.fixture(name="autodownsampling")
def fixture_autodownsampling() -> Generator[None, None, None]:
    """Enable auto downsampling with a small maximum number of points, then restore
    the options"""
    conf = get_conf()
    options = (conf.sig_autodownsampling, conf.sig_autodownsampling_maxpoints)
    old_values = [option.get() for option in options]
    conf.sig_autodownsampling.set(True)
    conf.sig_autodownsampling_maxpoints.set(MAXPOINTS)
    try:
        with qt_app_context(exec_loop=False):
            yield
    finally:
        for option, value in zip(options, old_values):
            option.set(value)


def _make_adapter(size: int) -> SignalObjPlotPyAdapter:
    """Return the adapter of a new signal with a given number of points"""
    x = np.linspace(0.0, 1.0, size)
    obj = create_signal(f"Signal ({size} points)", x, np.sin(2 * np.pi * 50 * x))
    return create_adapter_from_object(obj)


def _check_downsampling(item: CurveItem, size: int, maxpoints: int) -> None:
    """Check the downsampling of a curve item

    Args:
        item: curve item
        size: number of points of the curve
        maxpoints: maximum number of points to draw (even number)
    """
    if size > maxpoints:
        assert item.param.use_dsamp
        assert item.param.dsamp_factor == math.ceil(size / maxpoints)
        # Keeping one point out of N draws at most `maxpoints` points, and min/max
        # downsampling (PlotPy >= 2.12) at most 2 more points (first and last points)
        assert item.dataSize() <= maxpoints + 2
    else:
        assert not item.param.use_dsamp
        assert item.dataSize() == size


@pytest.mark.usefixtures("autodownsampling")
@pytest.mark.parametrize(
    "size",
    [
        MAXPOINTS // 2,
        MAXPOINTS,
        MAXPOINTS + 1,
        5 * MAXPOINTS,
        5 * MAXPOINTS + 1,
        6 * MAXPOINTS - 1,
    ],
)
def test_downsampling_threshold(size: int) -> None:
    """Curves with more points than the maximum number of points are downsampled,
    and are drawn with at most this number of points"""
    item = _make_adapter(size).make_item()
    _check_downsampling(item, size, MAXPOINTS)


@pytest.mark.usefixtures("autodownsampling")
def test_downsampling_disabled() -> None:
    """Curves are not downsampled when auto downsampling is disabled"""
    get_conf().sig_autodownsampling.set(False)
    size = 10 * MAXPOINTS
    item = _make_adapter(size).make_item()
    assert not item.param.use_dsamp
    assert item.dataSize() == size


@pytest.mark.usefixtures("autodownsampling")
def test_downsampling_factor_change() -> None:
    """The drawn data follow a change of the downsampling factor alone"""
    size = 20 * MAXPOINTS
    item = _make_adapter(size).make_item()
    _check_downsampling(item, size, MAXPOINTS)
    get_conf().sig_autodownsampling_maxpoints.set(2 * MAXPOINTS)
    apply_downsampling(item)
    _check_downsampling(item, size, 2 * MAXPOINTS)
    assert item.dataSize() > MAXPOINTS + 2


@pytest.mark.usefixtures("autodownsampling")
def test_update_item_follows_options() -> None:
    """Updating a plot item applies the current downsampling options"""
    size = 20 * MAXPOINTS
    adapter = _make_adapter(size)
    item = adapter.make_item()
    get_conf().sig_autodownsampling_maxpoints.set(4 * MAXPOINTS)
    adapter.update_item(item, data_changed=False)
    _check_downsampling(item, size, 4 * MAXPOINTS)
    get_conf().sig_autodownsampling.set(False)
    adapter.update_item(item, data_changed=False)
    assert not item.param.use_dsamp
    assert item.dataSize() == size
