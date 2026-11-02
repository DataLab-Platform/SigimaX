# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Window title bars on Windows
----------------------------

With the dark theme on Windows, Windows draws the title bar of windows with its own
color scheme: since guidata 3.17.2, every window is given a title bar following the
color theme, so that the SigimaX windows do not fix it themselves.

Covers (native Windows platform only, i.e. with ``--show-windows``):
- WarningErrorMessageBox, LogViewerWindow, Wizard, ConnectionDialog,
  H5BrowserDialog: dark title bar with the dark theme, light with the light theme
"""

from __future__ import annotations

import os
import time

import pytest
from guidata import qthelpers as qth
from guidata.qthelpers import qt_app_context
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from sigimax.widgets.connection import ConnectionDialog
from sigimax.widgets.h5browser import H5BrowserDialog
from sigimax.widgets.logviewer import LogViewerWindow
from sigimax.widgets.warningerror import WarningErrorMessageBox
from sigimax.widgets.wizard import ExampleWizard

pytestmark = [
    pytest.mark.gui,
    pytest.mark.skipif(os.name != "nt", reason="Windows only"),
]


def is_dark_title_bar(widget: QW.QWidget) -> bool:
    """Return True if the title bar of a window is dark (Windows API)"""
    import ctypes  # pylint: disable=import-outside-toplevel
    from ctypes import wintypes  # pylint: disable=import-outside-toplevel

    value = wintypes.BOOL()
    hwnd = wintypes.HWND(int(widget.winId()))
    for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (Windows 10 20H1+)
        result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
        )
        if result == 0:
            return bool(value.value)
    raise OSError("DwmGetWindowAttribute failed")


def process_events(duration: float = 0.3) -> None:
    """Process pending events (the title bars may be given again after a color mode
    change, once Qt has processed it, e.g. with Qt 6)"""
    end = time.perf_counter() + duration
    while time.perf_counter() < end:
        QW.QApplication.processEvents()
        time.sleep(0.01)


def test_title_bars_follow_color_mode() -> None:
    """The title bar of SigimaX windows follows the color theme"""
    with qt_app_context():
        if QG.QGuiApplication.platformName() != "windows":
            pytest.skip("Native Windows platform only (use --show-windows)")
        process_events()  # e.g. pending closing of all the windows by previous tests
        initial_mode = qth.get_color_mode()
        windows: dict[str, QW.QWidget] = {}
        try:
            qth.set_color_mode(qth.DARK)
            windows = {
                "warning message box": WarningErrorMessageBox(
                    None, "warning", "Context", "Message"
                ),
                "log viewer": LogViewerWindow([]),
                "wizard": ExampleWizard(),
                "connection dialog": ConnectionDialog(lambda: None),
                "HDF5 browser": H5BrowserDialog(),
            }
            for window in windows.values():
                window.show()
            process_events()
            for name, window in windows.items():
                assert is_dark_title_bar(window), name
            qth.set_color_mode(qth.LIGHT)
            process_events()
            for name, window in windows.items():
                assert not is_dark_title_bar(window), name
        finally:
            for window in windows.values():
                window.close()
                window.deleteLater()
            QC.QCoreApplication.sendPostedEvents(None, QC.QEvent.DeferredDelete)
            qth.set_color_mode(initial_mode)
