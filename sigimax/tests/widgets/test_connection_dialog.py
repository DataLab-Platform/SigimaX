# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for the ConnectionDialog widget (:mod:`sigimax.widgets.connection`)
--------------------------------------------------------------------------

Covers:
- ConnectionThread success/failure signal emission
- ConnectionDialog construction (icon/banner, default error message)
- ConnectionDialog cancelled while connecting (attempt continued in the background)

Note: ``ConnectionDialog.exec()`` itself is not exercised here. Its modal
loop combines a background QThread with guidata's unattended auto-close
timer, which always force-accepts the dialog (see
``guidata.qthelpers.close_dialog_and_quit``) - this is why DataLab itself
never runs it through the automated test suite either (only a manual,
``guitest: show,skip`` script).
"""

from __future__ import annotations

import gc
import threading
import time

import pytest
from guidata.qthelpers import qt_app_context, qt_wait
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from sigimax.widgets import connection
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


@pytest.mark.parametrize(
    "exc, message",
    [
        (TimeoutError("timed out"), "timed out"),
        (OSError("name resolution failed"), "name resolution failed"),
        (RuntimeError(), "RuntimeError"),
    ],
)
def test_connection_thread_other_failures(exc: Exception, message: str):
    """The thread emits SIG_CONNECTION_KO whatever the error raised by the
    callback, so that the dialog does not wait forever."""

    def failing_connect() -> None:
        raise exc

    with qt_app_context():
        errors: list[str] = []
        successes: list[bool] = []
        thread = ConnectionThread(failing_connect)
        thread.SIG_CONNECTION_KO.connect(errors.append)
        thread.SIG_CONNECTION_OK.connect(lambda: successes.append(True))
        thread.start()
        thread.wait(2000)
        qt_wait(0.2)
    assert errors == [message]
    assert not successes


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


def _process_events_until(condition, timeout: float = 10.0) -> None:
    """Process Qt events until a condition is true"""
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "Condition not met"
        qt_wait(0.05)


@pytest.mark.parametrize("delete_dialog", [False, True])
def test_connection_dialog_cancelled_while_connecting(delete_dialog: bool):
    """Cancelling while connecting closes the dialog at once: the connection
    attempt continues in the background, and its result is ignored, even if the
    dialog has been deleted meanwhile."""
    release = threading.Event()

    def slow_connect() -> None:
        assert release.wait(10.0)

    with qt_app_context():
        # pylint: disable=protected-access
        dlg = ConnectionDialog(slow_connect)
        dlg._ConnectionDialog__connect_to_server()
        thread = dlg.thread
        status = dlg.status_label.text()
        dlg.reject()
        assert dlg.result() == QW.QDialog.Rejected
        assert thread in connection._DETACHED_THREADS
        if delete_dialog:
            dlg.deleteLater()
            del dlg
            qt_wait(0.1)
            gc.collect()
        release.set()
        _process_events_until(lambda: not connection._DETACHED_THREADS)
        assert thread.isFinished()
        if not delete_dialog:
            # The result of the attempt is not shown
            assert dlg.status_label.text() == status
            assert dlg.result() == QW.QDialog.Rejected


if __name__ == "__main__":
    test_connection_thread_success()
    test_connection_thread_failure()
    test_connection_thread_other_failures(TimeoutError("timed out"), "timed out")
    test_connection_dialog_construction_defaults()
    test_connection_dialog_construction_with_icon_and_banner()
    test_connection_dialog_cancelled_while_connecting(True)
