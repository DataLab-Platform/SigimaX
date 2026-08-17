# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Connection dialog
------------------

This module provides a dialog box showing the progress of a connection to a
DataLab-derived application server, to be used together with
:class:`sigima.client.SimpleRemoteProxy` (or any remote proxy exposing a
similarly blocking ``connect`` method).

.. autoclass:: ConnectionDialog
    :members:
"""

from __future__ import annotations

from collections.abc import Callable

from guidata.qthelpers import get_std_icon, win32_fix_title_bar_background
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from sigimax.config import _

__all__ = ["ConnectionDialog"]


class ConnectionThread(QC.QThread):
    """Connection thread, running the blocking connect callback in background.

    Args:
        connect_callback: Callback function to connect to the remote server
        parent: Parent object. Defaults to None.
    """

    SIG_CONNECTION_OK = QC.Signal()
    SIG_CONNECTION_KO = QC.Signal(str)

    def __init__(self, connect_callback: Callable, parent: QC.QObject = None) -> None:
        super().__init__(parent)
        self.connect_callback = connect_callback

    def run(self) -> None:
        """Run thread"""
        try:
            self.connect_callback()
            self.SIG_CONNECTION_OK.emit()
        except ConnectionRefusedError as exc:
            self.SIG_CONNECTION_KO.emit(str(exc))


class ConnectionDialog(QW.QDialog):
    """Connection dialog, showing the progress of a connection attempt.

    Args:
        connect_callback: Callback function to connect to the remote server
        parent: Parent widget. Defaults to None.
        icon: Window icon. Defaults to None (no icon override).
        banner: Optional banner pixmap displayed above the progress bar.
    """

    def __init__(
        self,
        connect_callback: Callable,
        parent: QW.QWidget = None,
        icon: QG.QIcon | None = None,
        banner: QG.QPixmap | None = None,
    ) -> None:
        super().__init__(parent)
        win32_fix_title_bar_background(self)
        self.setWindowTitle(_("Connection"))
        if icon is not None:
            self.setWindowIcon(icon)
        self.resize(300, 50)
        self.__error_message = ""
        layout = QW.QVBoxLayout()
        self.setLayout(layout)
        if banner is not None:
            banner_label = QW.QLabel()
            banner_label.setPixmap(banner)
            banner_label.setAlignment(QC.Qt.AlignCenter)
            layout.addWidget(banner_label)
        self.progress_bar = QW.QProgressBar()
        self.progress_bar.setRange(0, 0)
        status = QW.QWidget()
        status_layout = QW.QHBoxLayout()
        status.setLayout(status_layout)
        self.status_label = QW.QLabel(_("Waiting for connection..."))
        self.status_icon = QW.QLabel()
        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.status_label)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addStretch()
        layout.addWidget(self.progress_bar)
        layout.addWidget(status)
        self.thread = ConnectionThread(connect_callback)
        self.thread.SIG_CONNECTION_OK.connect(self.__on_connection_successful)
        self.thread.SIG_CONNECTION_KO.connect(self.__on_connection_failed)
        button_box = QW.QDialogButtonBox(QW.QDialogButtonBox.Cancel)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def __set_status_icon(self, name: str) -> None:
        """Set status icon with standard Qt icon name"""
        self.status_icon.setPixmap(QG.QPixmap(get_std_icon(name).pixmap(24)))

    def __connect_to_server(self) -> None:
        """Connect to server"""
        self.progress_bar.setRange(0, 0)
        self.__set_status_icon("BrowserReload")
        self.status_label.setText(_("Connecting to server..."))
        self.thread.start()

    def __on_connection_successful(self) -> None:
        """Connection successful"""
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.__set_status_icon("DialogApplyButton")
        self.status_label.setText(_("Connection successful!"))
        QC.QTimer.singleShot(1000, self.accept)

    def __on_connection_failed(self, error_message: str) -> None:
        """Connection failed"""
        self.__error_message = error_message
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.__set_status_icon("MessageBoxCritical")
        self.status_label.setText(_("Connection failed: %s") % error_message)
        QC.QTimer.singleShot(2000, self.reject)

    def get_error_message(self) -> str:
        """Get error message if connection failed"""
        return self.__error_message

    def exec(self) -> int:
        """Execute dialog"""
        self.__connect_to_server()
        return super().exec()
