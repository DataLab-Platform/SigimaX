# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Module providing a log viewer widget, a log viewer window and SigimaX's log viewer
"""

from __future__ import annotations

import os.path as osp

from guidata.configtools import get_icon
from guidata.qthelpers import exec_dialog
from qtpy import QtWidgets as QW

from sigimax.config import _, get_conf, get_old_log_fname
from sigimax.env import execenv
from sigimax.widgets.fileviewer import FileViewerWidget, get_title_contents

__all__ = [
    "LogViewerWindow",
    "exec_sigimax_logviewer_dialog",
    "get_log_filenames",
    "get_log_prompt_message",
]


class LogViewerWindow(QW.QDialog):
    """Log viewer window"""

    def __init__(self, fnames: list[str], parent: QW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("logviewer")
        self.setWindowTitle(get_conf().app_name.get() + " - " + _("Log files"))
        self.setWindowIcon(get_icon(get_conf().app_logo_path.get()))
        self.tabs = QW.QTabWidget(self)
        for fname in fnames:
            if osp.isfile(fname):
                title, contents = get_title_contents(fname)
                if not contents.strip():
                    continue
                viewer = FileViewerWidget(language="Python")
                viewer.set_data(title, contents)
                self.tabs.addTab(viewer, get_icon("logs.svg"), osp.basename(fname))
        layout = QW.QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.resize(900, 400)

    @property
    def is_empty(self) -> bool:
        """Return True if there is no log available"""
        return self.tabs.count() == 0


def get_log_filenames() -> list[str]:
    """Return log filenames"""
    conf = get_conf()
    return [
        conf.traceback_log_path.get(),
        conf.faulthandler_log_path.get(),
        get_old_log_fname(conf.traceback_log_path.get()),
        get_old_log_fname(conf.faulthandler_log_path.get()),
    ]


def get_log_prompt_message() -> str | None:
    """Return prompt message for log files, i.e. a message informing the user
    whether log files were generated during last session or current session."""
    avail = [osp.isfile(fname) for fname in get_log_filenames()]
    if avail[0] or avail[1]:
        return _("Log files were generated during current session.")
    if avail[2] or avail[3]:
        return _("Log files were generated during last session.")
    return None


def exec_sigimax_logviewer_dialog(parent: QW.QWidget | None = None) -> None:
    """View SigimaX logs"""
    fnames = [osp.normpath(fname) for fname in get_log_filenames() if osp.isfile(fname)]
    dlg = LogViewerWindow(fnames, parent=parent)
    if dlg.is_empty:
        if not execenv.unattended:
            QW.QMessageBox.information(
                dlg, get_conf().app_name.get(), _("Log files are currently empty.")
            )
        dlg.close()
    else:
        exec_dialog(dlg)
