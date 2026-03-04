# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for the application launcher (:mod:`sigimax.app`)
-------------------------------------------------------

Covers:
- create() with default args → returns SGMXMainWindow
- create() with console=True → window has console
- create() with custom size → window geometry matches
- create() with custom window_class → returns correct subclass
"""

from __future__ import annotations

import pytest

from sigimax.app import create as sigimax_create
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils.qthelpers import sigimax_app_context

pytestmark = pytest.mark.app


class _TestSubWindow(SGMXMainWindow):
    """Minimal subclass for testing window_class parameter."""

    CUSTOM_MARKER = True

    def __init__(self, console=None, hide_on_close=False):
        super().__init__(console=console, hide_on_close=hide_on_close)


def test_create_default():
    """create() with default args returns a SGMXMainWindow instance."""
    with sigimax_app_context(exec_loop=False):
        win = sigimax_create(splash=False)
        assert isinstance(win, SGMXMainWindow)
        win.close()


def test_create_with_console():
    """create() with console=True → window has an embedded console."""
    with sigimax_app_context(exec_loop=False):
        win = sigimax_create(splash=False, console=True)
        assert isinstance(win, SGMXMainWindow)
        # Console dock should exist
        assert win.docks is not None
        win.close()


def test_create_custom_size():
    """create() with custom size → window should be resized."""
    width, height = 800, 500
    with sigimax_app_context(exec_loop=False):
        win = sigimax_create(splash=False, size=(width, height))
        assert win.width() == width
        assert win.height() == height
        win.close()


def test_create_custom_window_class():
    """create() with a custom window_class returns an instance of that class."""
    with sigimax_app_context(exec_loop=False):
        win = sigimax_create(window_class=_TestSubWindow, splash=False)
        assert isinstance(win, _TestSubWindow)
        assert hasattr(win, "CUSTOM_MARKER")
        assert win.CUSTOM_MARKER is True
        win.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
