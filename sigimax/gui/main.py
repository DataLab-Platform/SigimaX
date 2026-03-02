# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Main window
===========

The :mod:`sigimax.gui.main` module provides a generic main window for derived
applications.
It is designed to be flexible and extensible, allowing to easily add
new panels, actions, menus and toolbars.
It also provides a set of signals to communicate with other parts of the application.

.. autoclass:: SGMXMainWindow
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

import abc
import base64
import os
import os.path as osp
import sys
import time
import webbrowser
from typing import TYPE_CHECKING

# import guidata.dataset as gds
import numpy as np
import scipy.ndimage as spi
import scipy.signal as sps
from guidata import qthelpers as guidata_qth
from guidata.configtools import get_icon
from guidata.qthelpers import add_actions, create_action, exec_dialog
from guidata.widgets.console import DockableConsole
from plotpy import config as plotpy_config

# from plotpy.builder import make
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW
from qtpy.compat import getopenfilenames, getsavefilename

# from qtpy.compat import getopenfilenames, getsavefilename
import sigimax
from sigimax import __homeurl__, env
from sigimax.config import CONF as Conf
from sigimax.config import (
    DEBUG,
    MOD_DESC,
    MOD_TITLE,
    TEST_SEGFAULT_ERROR,
    _,
)
from sigimax.env import execenv
from sigimax.gui.docks import DockablePlotWidget
from sigimax.h5 import H5Importer
from sigimax.utils import qthelpers as qth
from sigimax.utils.qthelpers import (
    add_corner_menu,
    bring_to_front,
    configure_menu_about_to_show,
    qt_handle_error_message,
)
from sigimax.widgets import logviewer, status
from sigimax.widgets.h5browser import H5BrowserDialog
from sigimax.widgets.warningerror import go_to_error

if TYPE_CHECKING:
    from typing import Literal


class SGMXMainWindowMeta(type(QW.QMainWindow), abc.ABCMeta):
    """Mixed metaclass to avoid conflicts"""


class SGMXMainWindow(QW.QMainWindow, metaclass=SGMXMainWindowMeta):
    """SigimaX generic main window

    Args:
        console: enable internal console
        hide_on_close: True to hide window on close
    """

    __instance = None

    SIG_READY = QC.Signal()
    SIG_SEND_OBJECT = QC.Signal(object)
    SIG_SEND_OBJECTLIST = QC.Signal(object)
    SIG_CLOSING = QC.Signal()

    @staticmethod
    def get_instance(console=None, hide_on_close=False):
        """Return singleton instance"""
        if SGMXMainWindow.__instance is None:
            return SGMXMainWindow(console, hide_on_close)
        return SGMXMainWindow.__instance

    def __init__(self, console=None, hide_on_close=False):
        """Initialize main window"""
        SGMXMainWindow.__instance = self
        super().__init__()
        self.setObjectName(Conf.app_name.get())
        self.setWindowIcon(get_icon(Conf.app_logo_path.get()))

        execenv.log(self, "Starting initialization")

        self.ready_flag = True

        self.hide_on_close = hide_on_close
        self.__old_size: tuple[int, int] | None = None
        self.__memory_warning = False
        self.memorystatus: status.MemoryStatus | None = None

        self.consolestatus: status.ConsoleStatus | None = None
        self.console: DockableConsole | None = None

        self.main_toolbar: QW.QToolBar | None = None
        self.tabwidget: QW.QTabWidget | None = None
        self.tabmenu: QW.QMenu | None = None
        self.docks: dict[DockableConsole, QW.QDockWidget] = {}

        self.openh5_action: QW.QAction | None = None
        self.saveh5_action: QW.QAction | None = None
        self.browseh5_action: QW.QAction | None = None
        self.settings_action: QW.QAction | None = None
        self.quit_action: QW.QAction | None = None
        self.showfirstonly_action: QW.QAction | None = None
        self.showlabel_action: QW.QAction | None = None

        self.file_menu: QW.QMenu | None = None
        self.view_menu: QW.QMenu | None = None
        self.help_menu: QW.QMenu | None = None

        self.__update_color_mode(startup=True)

        self.__is_modified = False
        self.set_modified(False)

        # Setup actions and menus
        if console is None:
            console = Conf.console_enabled.get()
        self.setup(console)

        self.__restore_pos_and_size()
        execenv.log(self, "Initialization done")

    def __set_low_memory_state(self, state: bool) -> None:
        """Set memory warning state"""
        self.__memory_warning = state

    def confirm_memory_state(self) -> bool:  # pragma: no cover
        """Check memory warning state and eventually show a warning dialog

        Returns:
            True if memory state is ok
        """
        if not env.execenv.unattended and self.__memory_warning:
            threshold = Conf.available_memory_threshold.get()
            answer = QW.QMessageBox.critical(
                self,
                _("Warning"),
                _("Available memory is below %d MB.<br><br>Do you want to continue?")
                % threshold,
                QW.QMessageBox.Yes | QW.QMessageBox.No,
            )
            return answer == QW.QMessageBox.Yes
        return True

    def check_stable_release(self) -> None:  # pragma: no cover
        """Check if this is a stable release"""
        if sigimax.__version__.replace(".", "").isdigit():
            # This is a stable release
            return
        if "b" in sigimax.__version__:
            # This is a beta release
            rel = _(
                "This software is in the <b>beta stage</b> of its release cycle. "
                "The focus of beta testing is providing a feature complete "
                "software for users interested in trying new features before "
                "the final release. However, <u>beta software may not behave as "
                "expected and will probably have more bugs or performance issues "
                "than completed software</u>."
            )
        else:
            # This is an alpha release
            rel = _(
                "This software is in the <b>alpha stage</b> of its release cycle. "
                "The focus of alpha testing is providing an incomplete software "
                "for early testing of specific features by users. "
                "Please note that <u>alpha software was not thoroughly tested</u> "
                "by the developer before it is released."
            )
        txtlist = [
            f"<b>{Conf.app_name.get()}</b> v{Conf.app_version.get()}:",
            "",
            _("<i>This is not a stable release.</i>"),
            "",
            rel,
        ]
        if not env.execenv.unattended:
            QW.QMessageBox.warning(
                self, Conf.app_name.get(), "<br>".join(txtlist), QW.QMessageBox.Ok
            )

    def check_for_previous_crash(self) -> None:  # pragma: no cover
        """Check for previous crash"""
        if execenv.unattended and not execenv.do_not_quit:
            # Showing the log viewer for testing purpose (unattended mode) but only
            # if option 'do_not_quit' is not set, to avoid blocking the test suite
            self.__show_logviewer()
        elif execenv.do_not_quit:
            # If 'do_not_quit' is set, we do not show any message box to avoid blocking
            # the test suite
            return
        elif Conf.faulthandler_log_available.get(
            False
        ) or Conf.traceback_log_available.get(False):
            txt = "<br>".join(
                [
                    logviewer.get_log_prompt_message(),
                    "",
                    _("Do you want to see available log files?"),
                ]
            )
            btns = QW.QMessageBox.StandardButton.Yes | QW.QMessageBox.StandardButton.No
            choice = QW.QMessageBox.warning(self, Conf.app_name.get(), txt, btns)
            if choice == QW.QMessageBox.StandardButton.Yes:
                self.__show_logviewer()

    def execute_post_show_actions(self) -> None:
        """Execute post-show actions"""
        self.check_stable_release()
        self.check_for_previous_crash()

    def take_screenshot(self, name: str) -> None:  # pragma: no cover
        """Take main window screenshot"""
        # For esthetic reasons, we set the central widget width to a lower value:
        old_width = self.tabwidget.maximumWidth()
        self.tabwidget.setMaximumWidth(500)
        # To avoid having screenshot depending on memory status, we set demo mode ON:
        self.memorystatus.set_demo_mode(True)
        qth.grab_save_window(self, f"{name}")
        # Restore previous state:
        self.memorystatus.set_demo_mode(False)
        self.tabwidget.setMaximumWidth(old_width)

    def take_menu_screenshots(self) -> None:  # pragma: no cover
        """Take menu screenshots"""
        for name in (
            "file",
            "view",
            "help",
        ):
            menu = getattr(self, f"{name}_menu")
            menu.popup(self.pos())
            qth.grab_save_window(menu, f"{name}_menu")
            menu.close()

    # ------GUI setup
    def __restore_pos_and_size(self) -> None:
        """Restore main window position and size from configuration"""
        pos = Conf.window_position.get(None)
        if pos is not None:
            posx, posy = pos
            self.move(QC.QPoint(posx, posy))
        size = Conf.window_size.get(None)
        if size is None:
            sgeo = self.screen().availableGeometry()
            sw, sh = sgeo.width(), sgeo.height()
            w = max(1200, min(1800, int(sw * 0.8)))
            h = max(700, min(1100, int(sh * 0.8)))
            size = (w, h)
            if pos is None:
                cx = sgeo.x() + (sw - w) // 2
                cy = sgeo.y() + (sh - h) // 2
                self.move(QC.QPoint(cx, cy))
        width, height = size
        self.resize(QC.QSize(width, height))
        if pos is not None and size is not None:
            sgeo = self.screen().availableGeometry()
            out_inf = posx < -int(0.9 * width) or posy < -int(0.9 * height)
            out_sup = posx > int(0.9 * sgeo.width()) or posy > int(0.9 * sgeo.height())
            if len(QW.QApplication.screens()) == 1 and (out_inf or out_sup):
                #  Main window is offscreen
                posx = min(max(posx, 0), sgeo.width() - width)
                posy = min(max(posy, 0), sgeo.height() - height)
                self.move(QC.QPoint(posx, posy))

    def __restore_state(self) -> None:
        """Restore main window state from configuration"""
        state = Conf.window_state.get(None)
        if state is not None:
            state = base64.b64decode(state)
            self.restoreState(QC.QByteArray(state))
            for widget in self.children():
                if isinstance(widget, QW.QDockWidget):
                    self.restoreDockWidget(widget)

    def __save_pos_size_and_state(self) -> None:
        """Save main window position, size and state to configuration"""
        is_maximized = self.windowState() == QC.Qt.WindowMaximized
        Conf.window_maximized.set(is_maximized)
        if not is_maximized:
            size = self.size()
            Conf.window_size.set((size.width(), size.height()))
            pos = self.pos()
            Conf.window_position.set((pos.x(), pos.y()))
        # Encoding window state into base64 string to avoid sending binary data
        # to the configuration file:
        state = base64.b64encode(self.saveState().data()).decode("ascii")
        Conf.window_state.set(state)

    def setup(self, console: bool = False) -> None:
        """Setup main window

        Args:
            console: True to setup console
        """
        self.__configure_statusbar(console)
        self.__setup_global_actions()
        self.__setup_central_widget()
        self.__add_menus()
        if console:
            self.__setup_console()
        # Now that everything is set up, we can restore the window state:
        self.__restore_state()

    def __configure_statusbar(self, console: bool) -> None:
        """Configure status bar

        Args:
            console: True if console is enabled
        """
        self.statusBar().showMessage(_("Welcome to %s!") % Conf.app_name.get(), 5000)
        if console:
            # Console status
            self.consolestatus = status.ConsoleStatus()
            self.statusBar().addPermanentWidget(self.consolestatus)
        # Memory status
        threshold = Conf.available_memory_threshold.get()
        self.memorystatus = status.MemoryStatus(threshold)
        self.memorystatus.SIG_MEMORY_ALARM.connect(self.__set_low_memory_state)
        self.statusBar().addPermanentWidget(self.memorystatus)

    def __add_toolbar(
        self, title: str, position: Literal["top", "bottom", "left", "right"], name: str
    ) -> QW.QToolBar:
        """Add toolbar to main window

        Args:
            title: toolbar title
            position: toolbar position
            name: toolbar name (Qt object name)
        """
        toolbar = QW.QToolBar(title, self)
        toolbar.setObjectName(name)
        area = getattr(QC.Qt, f"{position.capitalize()}ToolBarArea")
        self.addToolBar(area, toolbar)
        return toolbar

    def __setup_global_actions(self) -> None:
        """Setup global actions"""
        # TODO : setup H5 actions generically (check if we keep them in SigimaX)
        self.openh5_action = create_action(
            self,
            _("Open HDF5 files..."),
            icon=get_icon("fileopen_h5.svg"),
            tip=_("Open one or more HDF5 files"),
            triggered=lambda checked=False: self.open_h5_files(import_all=True),
        )
        self.saveh5_action = create_action(
            self,
            _("Save to HDF5 file..."),
            icon=get_icon("filesave_h5.svg"),
            tip=_("Save to HDF5 file"),
            triggered=self.save_to_h5_file,
        )
        self.browseh5_action = create_action(
            self,
            _("Browse HDF5 file..."),
            icon=get_icon("h5browser.svg"),
            tip=_("Browse an HDF5 file"),
            triggered=lambda checked=False: self.open_h5_files(import_all=None),
        )
        self.main_toolbar = self.__add_toolbar(
            _("Main Toolbar"), "left", "main_toolbar"
        )
        add_actions(
            self.main_toolbar,
            [
                self.openh5_action,
                self.saveh5_action,
                self.browseh5_action,
                None,
                self.settings_action,
            ],
        )
        # Quit action for "File menu" (added when populating menu on demand)
        if self.hide_on_close:
            quit_text = _("Hide window")
            quit_tip = _("Hide window")
        else:
            quit_text = _("Quit")
            quit_tip = _("Quit application")
        if sys.platform != "darwin":
            # On macOS, the "Quit" action is automatically added to the application menu
            self.quit_action = create_action(
                self,
                quit_text,
                shortcut=QG.QKeySequence(QG.QKeySequence.Quit),
                icon=get_icon("libre-gui-close.svg"),
                tip=quit_tip,
                triggered=self.close,
            )

    def __setup_central_widget(self) -> None:
        """Setup central widget (main panel)"""
        # Apply enhanced tab bar styling
        self.tabwidget = QW.QTabWidget()
        self.tabmenu = add_corner_menu(self.tabwidget)
        tab_bar = self.tabwidget.tabBar()
        font = tab_bar.font()
        font.setPointSize(10)
        tab_bar.setFont(font)
        # Use QTimer to ensure tab bar is properly sized first
        QC.QTimer.singleShot(0, self.__update_tab_icon_size)

        self.setCentralWidget(self.tabwidget)

    def __update_tab_icon_size(self) -> None:
        """Update tab icon size based on tab bar height"""
        if self.tabwidget is not None:
            tab_bar = self.tabwidget.tabBar()
            if tab_bar.height() > 0:
                # Use approximately 80% of tab height for icon size
                icon_size = int(tab_bar.height() * 0.8)
                self.tabwidget.setIconSize(QC.QSize(icon_size, icon_size))

    @staticmethod
    def __get_local_doc_path() -> str | None:
        """Return local documentation path, if it exists.

        Uses the ``app_local_doc_path`` config field. When the path pattern
        contains ``{lang}``, the system locale prefix is tried first (e.g.
        ``fr``), then ``en`` as fallback. If the pattern does not contain
        ``{lang}``, it is used as-is.

        Returns:
            Resolved file path, or None if not configured / not found.
        """
        pattern = Conf.app_local_doc_path.get()
        if not pattern:
            return None
        if "{lang}" in pattern:
            locale = QC.QLocale.system().name()
            for lang in (locale[:2], "en"):
                path = pattern.format(lang=lang)
                if osp.isfile(path):
                    return path
        else:
            if osp.isfile(pattern):
                return pattern
        return None

    def __add_menus(self) -> None:
        """Adding menus"""
        self.file_menu = self.menuBar().addMenu(_("&File"))
        configure_menu_about_to_show(self.file_menu, self.__update_file_menu)
        self.view_menu = self.menuBar().addMenu(_("&View"))
        configure_menu_about_to_show(self.view_menu, self.__update_view_menu)
        self.help_menu = self.menuBar().addMenu("?")
        help_menu_actions = [
            create_action(
                self,
                _("Online documentation"),
                icon=get_icon("libre-gui-help.svg"),
                triggered=lambda: webbrowser.open(Conf.app_docurl.get()),
            ),
        ]
        localdocpath = self.__get_local_doc_path()
        if localdocpath is not None:
            help_menu_actions += [
                create_action(
                    self,
                    _("PDF documentation"),
                    icon=get_icon("help_pdf.svg"),
                    triggered=lambda: webbrowser.open(localdocpath),
                ),
            ]
        if TEST_SEGFAULT_ERROR:
            help_menu_actions += [
                create_action(
                    self,
                    _("Test segfault/Python error"),
                    triggered=self.test_segfault_error,
                )
            ]
        help_menu_actions += [
            create_action(
                self,
                _("Log files") + "...",
                icon=get_icon("logs.svg"),
                triggered=self.__show_logviewer,
            ),
            None,
            create_action(
                self,
                _("Project home page"),
                icon=get_icon("libre-gui-globe.svg"),
                triggered=lambda: webbrowser.open(Conf.app_homeurl.get()),
            ),
            create_action(
                self,
                _("Bug report or feature request"),
                icon=get_icon("libre-gui-globe.svg"),
                triggered=lambda: webbrowser.open(Conf.app_supporturl.get()),
            ),
            create_action(
                self,
                _("About..."),
                icon=get_icon("libre-gui-about.svg"),
                triggered=self._about,
            ),
        ]
        add_actions(self.help_menu, help_menu_actions)

    def __update_console_show_mode(self) -> None:
        """Update console show mode from configuration option

        Console show mode is whether the console is shown or not when an error occurs.
        """
        if self.console is not None:
            state = Conf.show_console_on_error.get()
            cdock = self.docks[self.console]
            if not state and cdock.isVisible():
                cdock.hide()
            if state:
                self.console.exception_occurred.connect(self.console.show_console)
            else:
                self.console.exception_occurred.disconnect(self.console.show_console)

    def __setup_console(self) -> None:
        """Add an internal console"""
        # TODO "dl" command in console ? Check if we keep it in SigimaX
        ns = {
            "dl": self,
            "np": np,
            "sps": sps,
            "spi": spi,
            "os": os,
            "sys": sys,
            "osp": osp,
            "time": time,
        }
        msg = _(
            "Welcome to SigimaX console!\n"
            "---------------------------\n"
            "You can access the main window with the 'dl' variable.\n"
            "Example:\n"
            "  o = dl.get_object()  # returns currently selected object\n"
            "  o = dl[1]  # returns object number 1\n"
            "  o = dl['My image']  # returns object which title is 'My image'\n"
            "  o.data  # returns object data\n"
            "Modules imported at startup: "
            "os, sys, os.path as osp, time, "
            "numpy as np, scipy.signal as sps, scipy.ndimage as spi"
        )
        self.console = DockableConsole(self, namespace=ns, message=msg, debug=DEBUG)
        self.console.setMaximumBlockCount(Conf.console_max_line_count.get(5000))
        self.console.go_to_error.connect(go_to_error)
        cdock = self.__add_dockwidget(self.console, _("Console"))
        self.docks[self.console] = cdock
        cdock.hide()
        self.__update_console_show_mode()
        self.console.exception_occurred.connect(self.consolestatus.exception_occurred)
        cdock.visibilityChanged.connect(self.consolestatus.console_visibility_changed)
        self.consolestatus.SIG_SHOW_CONSOLE.connect(self.console.show_console)

    def set_modified(self, state: bool = True) -> None:
        """Set mainwindow modified state"""
        self.__is_modified = state
        title = Conf.app_name.get() + ("*" if state else "")
        if not Conf.app_version.get().replace(".", "").isdigit():
            title += f" [{Conf.app_version.get()}]"
        self.setWindowTitle(title)

    def is_modified(self) -> bool:
        """Return True if mainwindow is modified"""
        return self.__is_modified

    def __add_dockwidget(self, child, title: str) -> QW.QDockWidget:
        """Add QDockWidget and toggleViewAction"""
        dockwidget, location = child.create_dockwidget(title)
        dockwidget.setObjectName(title)
        self.addDockWidget(location, dockwidget)
        return dockwidget

    def __update_file_menu(self) -> None:
        """Update file menu before showing up"""
        self.saveh5_action.setEnabled(
            True
        )  # TODO enable/disable based on workspace state
        add_actions(
            self.file_menu,
            [
                None,
                self.openh5_action,
                self.saveh5_action,
                self.browseh5_action,
                None,
                self.settings_action,
            ],
        )

    def __update_view_menu(self) -> None:
        """Update view menu before showing up"""
        add_actions(self.view_menu, [None] + self.createPopupMenu().actions())

    @staticmethod
    def __check_h5file(filename: str, operation: str) -> str:
        """Check HDF5 filename"""
        filename = osp.abspath(osp.normpath(filename))
        bname = osp.basename(filename)
        if operation == "load" and not osp.isfile(filename):
            raise IOError(f'File not found "{bname}"')
        Conf.base_dir.set(filename)
        return filename

    def save_to_h5_file(self, filename=None) -> None:
        """Save to a HDF5 file

        Args:
            filename: HDF5 filename. If None, a file dialog is opened.

        Raises:
            IOError: if filename is invalid or file cannot be saved.
        """
        if filename is None:
            basedir = Conf.base_dir.get()
            with qth.save_restore_stds():
                filename, _fl = getsavefilename(
                    self,
                    _("Save"),
                    basedir,
                    "HDF5 (*.h5 *.hdf5 *.hdf *.he5);;All files (*)",
                )
            if not filename:
                return
        with qth.qt_try_loadsave_file(self, filename, "save"):
            self.save_h5_workspace(filename)

    def open_h5_files(
        self,
        h5files: list[str] | None = None,
        import_all: bool | None = None,
        reset_all: bool | None = None,
    ) -> None:
        """Open/import HDF5 files.

        Args:
            h5files: HDF5 filenames (optionally with dataset name, separated by ":")
            import_all: Import all datasets from HDF5 files
            reset_all: Reset all application data before importing
        """
        if not self.confirm_memory_state():
            return
        if reset_all is None:
            # When workspace is empty, always preserve UUIDs (reset_all=True)
            # since there's no risk of conflicts
            reset_all = Conf.h5_clear_workspace.get()
            if Conf.h5_clear_workspace_ask.get():
                # Build message with optional note for native workspace import
                msg = _(
                    "Do you want to clear current workspace "
                    "before importing data from "
                    "HDF5 files?"
                )
                if import_all:
                    msg += "<br><br>" + _(
                        "<u>Note:</u> If you choose <i>No</i>, when importing "
                        "workspace files, objects with conflicting "
                        "identifiers will have their processing history lost "
                        "(features like 'Show source' and 'Recompute' will not "
                        "work for those objects). Non-conflicting objects will "
                        "preserve their processing history."
                    )
                msg += "<br><br>" + _(
                    "Choosing to ignore this message will prevent it "
                    "from being displayed again, and will use the "
                    "current setting (%s)."
                ) % (_("Yes") if reset_all else _("No"))
                answer = QW.QMessageBox.question(
                    self,
                    _("Warning"),
                    msg,
                    QW.QMessageBox.Yes | QW.QMessageBox.No | QW.QMessageBox.Ignore,
                )
                if answer == QW.QMessageBox.Yes:
                    reset_all = True
                elif answer == QW.QMessageBox.No:
                    reset_all = False
                elif answer == QW.QMessageBox.Ignore:
                    Conf.h5_clear_workspace_ask.set(False)
        if h5files is None:
            basedir = Conf.base_dir.get()
            with qth.save_restore_stds():
                h5files, _fl = getopenfilenames(
                    self,
                    _("Open"),
                    basedir,
                    _("HDF5 files (*.h5 *.hdf5 *.hdf *.he5);;All files (*)"),
                )
        if not h5files:
            return
        filenames, dsetnames = [], []
        for fname_with_dset in h5files:
            if "," in fname_with_dset:
                filename, dsetname = fname_with_dset.split(",")
                dsetnames.append(dsetname)
            else:
                filename = fname_with_dset
                dsetnames.append(None)
            filenames.append(filename)
        if import_all is None and all(dsetname is None for dsetname in dsetnames):
            self.browse_h5_files(filenames, reset_all)
            return
        for filename, dsetname in zip(filenames, dsetnames):
            if import_all is None and dsetname is None:
                self.import_h5_file(filename, reset_all)
            else:
                with qth.qt_try_loadsave_file(self, filename, "load"):
                    filename = self.__check_h5file(filename, "load")
                    self.import_dataset_from_file(
                        filename, dsetname, import_all, reset_all
                    )
            reset_all = False

    def import_dataset_from_file(
        self,
        filename: str,
        dsetname: str | None,
        import_all: bool | None,
        reset_all: bool,
    ) -> None:
        """Import a specific dataset from an HDF5 file.

        This is a hook for derived applications to handle dataset-specific
        import logic. The base implementation is a no-op; subclasses should
        override this method to implement their own import strategy.

        Args:
            filename: Path to the HDF5 file (already validated)
            dsetname: Dataset name to import, or ``None`` to import all
            import_all: If ``True``, import all datasets without browsing
            reset_all: If ``True``, clear workspace before importing
        """

    def browse_h5_files(
        self, filenames: list[str], _reset_all: bool | None = None
    ) -> None:
        """Browse HDF5 files

        Opens an :class:`H5BrowserDialog <sigimax.widgets.h5browser.H5BrowserDialog>`
        pre-loaded with the given *filenames*, lets the user check datasets to
        import, converts the checked nodes into native objects
        (:class:`SignalObj <sigima.objects.SignalObj>` /
        :class:`ImageObj <sigima.objects.ImageObj>`), and emits them via
        :data:`SIG_SEND_OBJECTLIST`.

        Args:
            filenames: HDF5 filenames
            _reset_all: Reset all application data before importing (unused)
        """
        for filename in filenames:
            self.__check_h5file(filename, "load")

        dialog = H5BrowserDialog(self)
        dialog.open_files(filenames)

        if exec_dialog(dialog) == QW.QDialog.Accepted:
            nodes = dialog.get_nodes()
            if not nodes:
                dialog.cleanup()
                return
            objects = []
            for node in nodes:
                try:
                    obj = node.get_native_object()
                    if obj is not None:
                        objects.append(obj)
                except (OSError, ValueError) as exc:
                    qt_handle_error_message(self, exc)
            dialog.cleanup()
            if objects:
                self.SIG_SEND_OBJECTLIST.emit(objects)
                self.set_modified(True)
                self.statusBar().showMessage(
                    _("%d object(s) imported successfully") % len(objects),
                    5000,
                )
        else:
            dialog.cleanup()

    def save_h5_workspace(self, filename: str) -> None:
        """Save current workspace to an HDF5 file.

        The base implementation is a **no-op**: it validates the filename and
        clears the modified flag but does not write any data.  Subclasses that
        manage a data model should override this method to perform the actual
        serialization (e.g. using :class:`guidata.io.HDF5Writer`).

        Args:
            filename: HDF5 filename to save to

        Raises:
            IOError: If *filename* is invalid
        """
        filename = self.__check_h5file(filename, "save")
        execenv.log(
            self,
            "save_h5_workspace: no-op — override in subclass to serialize data",
        )
        self.set_modified(False)

    def import_h5_file(self, filename: str, _reset_all: bool | None = None) -> None:
        """Import all supported datasets from an HDF5 file (no dialog).

        Uses :class:`H5Importer <sigimax.h5.H5Importer>` to scan the file,
        converts every supported node into a native object
        (:class:`SignalObj <sigima.objects.SignalObj>` /
        :class:`ImageObj <sigima.objects.ImageObj>`), and emits the list via
        :data:`SIG_SEND_OBJECTLIST`.

        Args:
            filename: HDF5 filename
            _reset_all: Reserved for future use (workspace reset before import) (unused)
        """
        with qth.qt_try_loadsave_file(self, filename, "load"):
            filename = self.__check_h5file(filename, "load")
            importer = H5Importer(filename)
            objects = []
            for node in importer.nodes:
                if not node.is_supported():
                    continue
                try:
                    obj = node.get_native_object()
                    if obj is not None:
                        objects.append(obj)
                except Exception as exc:  # pylint: disable=broad-except
                    qt_handle_error_message(self, exc)
            importer.close()
            if objects:
                self.SIG_SEND_OBJECTLIST.emit(objects)
                self.set_modified(True)
                self.statusBar().showMessage(
                    _("%d object(s) imported successfully") % len(objects),
                    5000,
                )

    def get_version(self) -> str:
        """Return SigimaX public version.

        Returns:
            SigimaX version
        """
        # TODO generic app version (the one which implements sigimax )
        return sigimax.__version__

    def close_application(self) -> None:
        """Close SigimaX application"""
        self.close()

    def raise_window(self) -> None:
        """Raise SigimaX main window"""
        bring_to_front(self)

    def _about(self) -> None:  # pragma: no cover
        """About dialog box.

        Override this method in subclasses to fully customize the About dialog.
        """
        self.check_stable_release()
        if Conf.process_isolation_enabled.get():
            pistate = "<font color='green'>" + _("enabled") + "</font>"
        else:
            pistate = "<font color='red'>" + _("disabled") + "</font>"
        adv_conf = "<br>".join(
            [
                "<i>" + _("Advanced configuration:") + "</i>",
                "• " + _("Process isolation:") + " " + pistate,
            ]
        )
        app_name = Conf.app_name.get()
        app_version = Conf.app_version.get()
        app_desc = Conf.app_desc.get()
        app_homeurl = Conf.app_homeurl.get()
        app_docurl = Conf.app_docurl.get()
        app_supporturl = Conf.app_supporturl.get()
        dev_by = Conf.app_developer.get()
        cprght = Conf.app_copyright.get()

        # -- Application header
        about_parts = [f"<b>{app_name}</b> v{app_version}"]
        if app_desc:
            about_parts.append(f"<br>{app_desc}")
        if dev_by:
            about_parts.append(f"<p>{dev_by}")
        if cprght:
            about_parts.append(f"<br>Copyright &copy; {cprght}")

        # -- Application links
        links = []
        if app_homeurl:
            links.append(f'<a href="{app_homeurl}">{_("Home page")}</a>')
        if app_docurl:
            links.append(f'<a href="{app_docurl}">{_("Documentation")}</a>')
        if app_supporturl:
            links.append(f'<a href="{app_supporturl}">{_("Support")}</a>')
        if links:
            about_parts.append("<p>" + " | ".join(links))

        # -- SigimaX credits
        sgmx_dev_by = _("Developed and maintained by DataLab open-source project team")
        sgmx_cprght = "2023 DataLab Platform Developers"
        about_parts.extend(
            [
                f'<p>Based on <a href="{__homeurl__}">{MOD_TITLE}</a>'
                f" v{sigimax.__version__}",
                f"<br>{MOD_DESC}",
                f"<br>{sgmx_dev_by}",
                f"<br>Copyright &copy; {sgmx_cprght}",
            ]
        )

        # -- Advanced configuration
        about_parts.append(f"<p>{adv_conf}")
        QW.QMessageBox.about(
            self,
            _("About") + " " + app_name,
            "".join(about_parts),
        )

    def __update_color_mode(self, startup: bool = False) -> None:
        """Update color mode

        Args:
            startup: True if method is called during application startup (in that case,
             color theme is applied only if mode != "auto")
        """
        mode = Conf.color_mode.get()
        if startup and mode == "auto":
            guidata_qth.win32_fix_title_bar_background(self)
            return

        # Prevent Qt from refreshing the window when changing the color mode:
        self.setUpdatesEnabled(False)

        plotpy_config.set_plotpy_color_mode(mode)

        if self.console is not None:
            self.console.update_color_mode()

        if self.docks is not None:
            for dock in self.docks.values():
                widget = dock.widget()
                if isinstance(widget, DockablePlotWidget):
                    widget.update_color_mode()

        # Allow Qt to refresh the window:
        self.setUpdatesEnabled(True)

    def __show_logviewer(self) -> None:
        """Show error logs"""
        logviewer.exec_sigimax_logviewer_dialog(self)

    @staticmethod
    def test_segfault_error() -> None:
        """Generate errors (both fault and traceback)"""
        import ctypes  # pylint: disable=import-outside-toplevel

        ctypes.string_at(0)
        raise RuntimeError("!!! Testing RuntimeError !!!")

    def show(self) -> None:
        """Reimplement QMainWindow method"""
        super().show()
        if self.__old_size is not None:
            self.resize(self.__old_size)

    # ------Close window
    def close_properly(self) -> bool:
        """Close properly

        Returns:
            True if closed properly, False otherwise
        """
        if not env.execenv.unattended and self.is_modified():
            answer = QW.QMessageBox.warning(
                self,
                _("Quit"),
                _(
                    "Do you want to save all signals and images "
                    "to an HDF5 file before quitting the application?"
                ),
                QW.QMessageBox.Yes | QW.QMessageBox.No | QW.QMessageBox.Cancel,
            )
            if answer == QW.QMessageBox.Yes:
                self.save_to_h5_file()
                if self.is_modified():
                    return False
            elif answer == QW.QMessageBox.Cancel:
                return False
        self.hide()  # Avoid showing individual widgets closing one after the other
        if self.console is not None:
            try:
                self.console.close()
            except RuntimeError:
                # TODO: [P3] Investigate further why the following error occurs when
                # restarting the mainwindow (this is *not* a production case):
                # "RuntimeError: wrapped C/C++ object of type DockableConsole
                #  has been deleted".
                # Another solution to avoid this error would be to really restart
                # the application (run each unit test in a separate process), but
                # it would represent too much effort for an error occuring in test
                # configurations only.
                pass
        # TODO check extract BasePanel and AbstractPanel
        # self.reset_all()
        self.__save_pos_size_and_state()

        # Saving current tab for next session
        Conf.current_tab.set(self.tabwidget.currentIndex())

        execenv.log(self, "closed properly")
        return True

    def closeEvent(self, event: QG.QCloseEvent) -> None:
        """Reimplement QMainWindow method"""
        if self.hide_on_close:
            self.__old_size = self.size()
            self.hide()
        else:
            if self.close_properly():
                self.SIG_CLOSING.emit()
                event.accept()
            else:
                event.ignore()
