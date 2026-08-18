# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for the ConnectionDialog widget (:mod:`sigimax.widgets.connection`)
--------------------------------------------------------------------------

Covers:
- ConnectionThread success/failure signal emission
- ConnectionDialog construction (icon/banner, default error message)

Note: ``ConnectionDialog.exec()`` itself is not exercised here. Its modal
loop combines a background QThread with guidata's unattended auto-close
timer, which always force-accepts the dialog (see
``guidata.qthelpers.close_dialog_and_quit``) - this is why DataLab itself
never runs it through the automated test suite either (only a manual,
``guitest: show,skip`` script).
"""

from __future__ import annotations

import pytest
from guidata.qthelpers import qt_app_context, qt_wait
from qtpy import QtGui as QG

from sigimax.widgets.connection import ConnectionDialog, ConnectionThread

pytestmark = pytest.mark.gui


def test_connection_thread_success():
    """The thread emits SIG_CONNECTION_OK when the callback succeeds."""
    with qt_app_context():
        calls: list[int] = []
        results: list[bool] = []
        thread = ConnectionThread(lambda: calls.append(1))
        thread.SIG_CONNECTION_OK.connect(lambda: results.append(True))
        thread.start()
        thread.wait(2000)
        qt_wait(0.2)
    assert calls == [1]
    assert results == [True]


def test_connection_thread_failure():
    """The thread emits SIG_CONNECTION_KO with the error message on failure."""

    def failing_connect() -> None:
        raise ConnectionRefusedError("no server listening")

    with qt_app_context():
        errors: list[str] = []
        thread = ConnectionThread(failing_connect)
        thread.SIG_CONNECTION_KO.connect(errors.append)
        thread.start()
        thread.wait(2000)
        qt_wait(0.2)
    assert errors == ["no server listening"]


def test_connection_dialog_construction_defaults():
    """A dialog builds with no icon/banner and an empty error message."""
    with qt_app_context():
        dlg = ConnectionDialog(lambda: None)
        assert dlg.get_error_message() == ""


def test_connection_dialog_construction_with_icon_and_banner():
    """A dialog accepts an optional icon and banner pixmap."""
    with qt_app_context():
        icon = QG.QIcon()
        banner = QG.QPixmap(10, 10)
        dlg = ConnectionDialog(lambda: None, icon=icon, banner=banner)
        assert dlg.get_error_message() == ""


if __name__ == "__main__":
    test_connection_thread_success()
    test_connection_thread_failure()
    test_connection_dialog_construction_defaults()
    test_connection_dialog_construction_with_icon_and_banner()
