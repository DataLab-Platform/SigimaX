# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Main window
===========

The :mod:`sigimax.mainwindow` module provides a generic main window for derived
applications.
It is designed to be flexible and extensible, allowing to easily add
new panels, actions, menus and toolbars.
It also provides a set of signals to communicate with other parts of the application.

.. autoclass:: SGMXMainWindow
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

__all__ = [
    "SGMXMainWindow",
]

import abc
import base64
import os
import os.path as osp
import sys
import time
import webbrowser
from typing import TYPE_CHECKING

import numpy as np
import scipy.ndimage as spi
import scipy.signal as sps
from guidata import qthelpers as guidata_qth
from guidata.configtools import get_icon
from guidata.qthelpers import add_actions, create_action, exec_dialog
from guidata.widgets.console import DockableConsole
from plotpy import config as plotpy_config
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW
from qtpy.compat import getopenfilenames, getsavefilename

from sigimax._metadata import __homeurl__, __version__
from sigimax.config import (
    DEBUG,
    MOD_DESC,
    MOD_TITLE,
    TEST_SEGFAULT_ERROR,
    _,
    get_conf,
)
from sigimax.env import execenv
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
from sigimax.widgets.plotdock import DockablePlotWidget
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

    #: Bump this whenever dock widget object names change, so that layouts saved
    #: by an older version are discarded instead of being partially restored.
    WINDOW_STATE_VERSION = 1

    SIG_READY = QC.Signal()
    SIG_SEND_OBJECT = QC.Signal(object)
    SIG_SEND_OBJECTLIST = QC.Signal(object)
    SIG_CLOSING = QC.Signal()

    @classmethod
    def get_instance(cls, console=None, hide_on_close=False):
        """Return the singleton instance for this window class."""
        if not isinstance(SGMXMainWindow.__instance, cls):
            return cls(console, hide_on_close)
        return SGMXMainWindow.__instance

    def __init__(self, console=None, hide_on_close=False):
        """Initialize main window"""
        SGMXMainWindow.__instance = self
        super().__init__()
        conf = get_conf()
        self.setObjectName(conf.app_name.get())
        self.setWindowIcon(get_icon(conf.app_logo_path.get()))

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
        self.docks: dict[QW.QWidget, QW.QDockWidget] = {}

        self.openh5_action: QW.QAction | None = None
        self.saveh5_action: QW.QAction | None = None
        self.browseh5_action: QW.QAction | None = None
        self.quit_action: QW.QAction | None = None
        self.showfirstonly_action: QW.QAction | None = None
        self.showlabel_action: QW.QAction | None = None

        self.file_menu: QW.QMenu | None = None
        self.view_menu: QW.QMenu | None = None
        self.help_menu: QW.QMenu | None = None

        # Setup actions and menus
        if console is None:
            console = conf.console_enabled.get()
        self._before_setup(console)
        self._update_color_mode(startup=True)

        self.__is_modified = False
        self.set_modified(False)
        self.setup(console)
        self._after_setup(console)

        self._restore_pos_and_size()
        execenv.log(self, "Initialization done")

    def _before_setup(self, console: bool) -> None:
        """Initialize derived-application state before :meth:`setup`.

        Args:
            console: Whether the internal console will be created.
        """

    def _after_setup(self, console: bool) -> None:
        """Finalize derived-application state after :meth:`setup`.

        Args:
            console: Whether the internal console was created.
        """

    def _set_low_memory_state(self, state: bool) -> None:
        """Set memory warning state"""
        self.__memory_warning = state

    def confirm_memory_state(self) -> bool:  # pragma: no cover
        """Check memory warning state and eventually show a warning dialog

        Returns:
            True if memory state is ok
        """
        if not execenv.unattended and self.__memory_warning:
            threshold = get_conf().available_memory_threshold.get()
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
        conf = get_conf()
        app_version = conf.app_version.get()
        if app_version.replace(".", "").isdigit():
            # This is a stable release
            return
        if "b" in app_version:
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
            f"<b>{conf.app_name.get()}</b> v{app_version}:",
            "",
            _("<i>This is not a stable release.</i>"),
            "",
            rel,
        ]
        if not execenv.unattended:
            QW.QMessageBox.warning(
                self, conf.app_name.get(), "<br>".join(txtlist), QW.QMessageBox.Ok
            )

    def check_for_previous_crash(self) -> None:  # pragma: no cover
        """Check for previous crash"""
        conf = get_conf()
        if execenv.unattended and not execenv.do_not_quit:
            # Showing the log viewer for testing purpose (unattended mode) but only
            # if option 'do_not_quit' is not set, to avoid blocking the test suite
            self._show_logviewer()
        elif execenv.do_not_quit:
            # If 'do_not_quit' is set, we do not show any message box to avoid blocking
            # the test suite
            return
        elif (
            conf.faulthandler_log_available.get() or conf.traceback_log_available.get()
        ):
            txt = "<br>".join(
                [
                    logviewer.get_log_prompt_message(),
                    "",
                    _("Do you want to see available log files?"),
                ]
            )
            btns = QW.QMessageBox.StandardButton.Yes | QW.QMessageBox.StandardButton.No
            choice = QW.QMessageBox.warning(self, conf.app_name.get(), txt, btns)
            if choice == QW.QMessageBox.StandardButton.Yes:
                self._show_logviewer()

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
    def _restore_pos_and_size(self) -> None:
        """Restore main window position and size from configuration"""
        conf = get_conf()
        pos = conf.window_position.get()
        if pos is not None:
            posx, posy = pos
            self.move(QC.QPoint(posx, posy))
        size = conf.window_size.get()
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

    def _restore_state(self) -> None:
        """Restore main window state from configuration"""
        state = get_conf().window_state.get()
        if state:
            state = base64.b64decode(state)
            self.restoreState(QC.QByteArray(state), self.WINDOW_STATE_VERSION)
            for widget in self.children():
                if isinstance(widget, QW.QDockWidget):
                    self.restoreDockWidget(widget)

    def _save_pos_size_and_state(self) -> None:
        """Save main window position, size and state to configuration"""
        conf = get_conf()
        is_maximized = self.windowState() == QC.Qt.WindowMaximized
        conf.window_maximized.set(is_maximized)
        if not is_maximized:
            size = self.size()
            conf.window_size.set((size.width(), size.height()))
            pos = self.pos()
            conf.window_position.set((pos.x(), pos.y()))
        # Encoding window state into base64 string to avoid sending binary data
        # to the configuration file:
        state = self.saveState(self.WINDOW_STATE_VERSION).data()
        conf.window_state.set(base64.b64encode(state).decode("ascii"))

    def setup(self, console: bool = False) -> None:
        """Setup main window

        The sequence is fixed: derived applications extend it by overriding the
        hooks it calls, not by overriding this method. :meth:`_restore_state`
        must stay last, since dock widgets added afterwards keep their default
        geometry instead of the persisted one.

        Args:
            console: True to setup console
        """
        self._configure_statusbar(console)
        self._setup_global_actions()
        self._setup_panels()
        self._setup_central_widget()
        self._add_menus()
        if console:
            self._setup_console()
        self._setup_docks()
        self._post_setup(console)
        # Now that everything is set up, we can restore the window state:
        self._restore_state()

    def _setup_panels(self) -> None:
        """Create the application panels and views.

        Called after the global actions, so that panel toolbars are added after
        the main toolbar, and before the central widget is set up.
        """

    def _setup_docks(self) -> None:
        """Add the application dock widgets.

        Called before :meth:`_restore_state`, so that the persisted layout is
        applied to them.
        """

    def _post_setup(self, console: bool) -> None:
        """Finalize the user interface.

        Called once panels, central widget, menus, console and docks all exist.

        Args:
            console: Whether the internal console was created.
        """

    def _configure_statusbar(self, console: bool) -> None:
        """Configure status bar

        Args:
            console: True if console is enabled
        """
        conf = get_conf()
        self.statusBar().showMessage(_("Welcome to %s!") % conf.app_name.get(), 5000)
        if console:
            # Console status
            self.consolestatus = status.ConsoleStatus()
            self.statusBar().addPermanentWidget(self.consolestatus)
        # Memory status
        threshold = conf.available_memory_threshold.get()
        self.memorystatus = status.MemoryStatus(threshold)
        self.memorystatus.SIG_MEMORY_ALARM.connect(self._set_low_memory_state)
        self.statusBar().addPermanentWidget(self.memorystatus)

    def _add_toolbar(
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

    def _setup_global_actions(self) -> None:
        """Setup global actions"""
        self._create_global_actions()
        self.main_toolbar = self._add_toolbar(_("Main Toolbar"), "left", "main_toolbar")
        add_actions(self.main_toolbar, self._get_main_toolbar_actions())

    def _create_global_actions(self) -> None:
        """Create global actions (H5, quit, etc.).

        Override in subclasses to create additional actions or replace
        defaults.  Call ``super()._create_global_actions()`` first to
        create the standard H5 and quit actions.
        """
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
        # Quit action for "File menu" (added when populating menu on demand)
        if self.hide_on_close:
            quit_text = _("Hide window")
            quit_tip = _("Hide %s window") % get_conf().app_name.get()
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

    def _get_main_toolbar_actions(self) -> list[QW.QAction | None]:
        """Return the list of actions for the main toolbar.

        Override in subclasses to customize which actions appear in the
        main toolbar and their order.  Return a list of :class:`QAction`
        instances (or ``None`` for separators).

        Returns:
            List of actions and separators
        """
        return [
            self.openh5_action,
            self.saveh5_action,
            self.browseh5_action,
        ]

    def _setup_central_widget(self) -> None:
        """Setup central widget (main panel)"""
        # Apply enhanced tab bar styling
        self.tabwidget = QW.QTabWidget()
        self.tabmenu = add_corner_menu(self.tabwidget)
        tab_bar = self.tabwidget.tabBar()
        font = tab_bar.font()
        font.setPointSize(10)
        tab_bar.setFont(font)
        # Use QTimer to ensure tab bar is properly sized first
        QC.QTimer.singleShot(0, self._update_tab_icon_size)

        self.setCentralWidget(self.tabwidget)

    def _update_tab_icon_size(self) -> None:
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
        pattern = get_conf().app_local_doc_path.get()
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

    def _get_menubar_layout(self) -> list[tuple[str, str]]:
        """Return the menu bar layout, as ``(attribute name, title)`` pairs.

        Each pair creates a menu stored as ``self.<attribute name>_menu``.
        Override in subclasses to insert application menus while keeping the
        standard ones, which the base implementation relies on.

        Returns:
            Ordered list of (attribute name, menu title)
        """
        return [("file", _("&File")), ("view", _("&View")), ("help", "?")]

    def _add_menus(self) -> None:
        """Adding menus"""
        for name, title in self._get_menubar_layout():
            setattr(self, f"{name}_menu", self.menuBar().addMenu(title))
        configure_menu_about_to_show(self.file_menu, self._update_file_menu)
        configure_menu_about_to_show(self.view_menu, self._update_view_menu)
        add_actions(self.help_menu, self._get_help_menu_actions())

    def _update_console_show_mode(self) -> None:
        """Update console show mode from configuration option

        Console show mode is whether the console is shown or not when an error occurs.
        """
        if self.console is not None:
            state = get_conf().show_console_on_error.get()
            cdock = self.docks[self.console]
            if not state and cdock.isVisible():
                cdock.hide()
            if state:
                self.console.exception_occurred.connect(self.console.show_console)
            else:
                self.console.exception_occurred.disconnect(self.console.show_console)

    def _get_console_namespace(self) -> dict[str, object]:
        """Return the namespace dict exposed in the internal console.

        The default namespace provides ``win`` (the main window) and commonly
        used scientific modules.  Override in subclasses to add
        application-specific variables.

        Returns:
            Namespace dictionary
        """
        return {
            "win": self,
            "np": np,
            "sps": sps,
            "spi": spi,
            "os": os,
            "sys": sys,
            "osp": osp,
            "time": time,
        }

    def _get_console_message(self) -> str:
        """Return the welcome message displayed in the internal console.

        Override in subclasses to provide application-specific examples.

        Returns:
            Welcome message string
        """
        app = get_conf().app_name.get()
        return (
            _(
                "Welcome to %s console!\n"
                "You can access the main window with the 'win' variable.\n"
                "Modules imported at startup: "
                "os, sys, os.path as osp, time, "
                "numpy as np, scipy.signal as sps, scipy.ndimage as spi"
            )
            % app
        )

    def _configure_console(self) -> None:
        """Configure application-specific console signals after creation."""

    def _setup_console(self) -> None:
        """Add an internal console"""
        ns = self._get_console_namespace()
        msg = self._get_console_message()
        self.console = DockableConsole(self, namespace=ns, message=msg, debug=DEBUG)
        self.console.setMaximumBlockCount(get_conf().console_max_line_count.get())
        self.console.go_to_error.connect(go_to_error)
        cdock = self._add_dockwidget(self.console, _("Console"), name="console")
        cdock.hide()
        self._update_console_show_mode()
        self.console.exception_occurred.connect(self.consolestatus.exception_occurred)
        cdock.visibilityChanged.connect(self.consolestatus.console_visibility_changed)
        self.consolestatus.SIG_SHOW_CONSOLE.connect(self.console.show_console)
        self._configure_console()

    def _normalize_modified_state(self, state: bool) -> bool:
        """Normalize a requested modified state for the application model."""
        return state

    def set_modified(self, state: bool = True) -> None:
        """Set mainwindow modified state"""
        state = self._normalize_modified_state(state)
        self.__is_modified = state
        if self.saveh5_action is not None:
            self.saveh5_action.setEnabled(self._is_save_enabled())
        conf = get_conf()
        title = conf.app_name.get() + ("*" if state else "")
        if not conf.app_version.get().replace(".", "").isdigit():
            title += f" [{conf.app_version.get()}]"
        self.setWindowTitle(title)

    def is_modified(self) -> bool:
        """Return True if mainwindow is modified"""
        return self.__is_modified

    def _add_dockwidget(
        self,
        child,
        title: str,
        *,
        name: str | None = None,
        key: QW.QWidget | None = None,
        tabify_with: QW.QWidget | None = None,
    ) -> QW.QDockWidget:
        """Add a dock widget to the main window and register it in ``self.docks``.

        Args:
            child: dockable widget, providing a ``create_dockwidget`` method
            title: dock widget title, displayed to the user (translated)
            name: stable Qt object name used to persist the dock layout. Defaults
             to ``title``, but a non-translated name should be passed so that the
             layout survives a language change.
            key: key used to register the dock in ``self.docks``, when the logical
             owner differs from the dockable widget itself. Defaults to ``child``.
            tabify_with: key of an already registered dock to tabify with

        Returns:
            Created dock widget
        """
        dockwidget, location = child.create_dockwidget(title)
        dockwidget.setObjectName(title if name is None else name)
        self.addDockWidget(location, dockwidget)
        if tabify_with is not None:
            self.tabifyDockWidget(self.docks[tabify_with], dockwidget)
        self.docks[child if key is None else key] = dockwidget
        return dockwidget

    def _is_save_enabled(self) -> bool:
        """Return whether the 'Save' action should be enabled.

        The base implementation returns ``True`` only when the workspace has
        been modified and the derived application overrides
        :meth:`save_h5_workspace`. Override in subclasses to add
        domain-specific conditions (e.g., whether the workspace contains any
        objects).

        Returns:
            True if save action should be enabled
        """
        return self._has_h5_workspace_persistence() and self.is_modified()

    def _get_file_menu_actions(self) -> list[QW.QAction | None]:
        """Return the list of actions for the file menu.

        Override in subclasses to fully customize which actions appear and
        their order.  Return a list of :class:`QAction` instances (or
        ``None`` for separators).

        Returns:
            List of actions and separators
        """
        return [
            None,
            self.openh5_action,
            self.saveh5_action,
            self.browseh5_action,
        ]

    def _update_file_menu(self) -> None:
        """Update file menu before showing up.

        Updates action states (via :meth:`_is_save_enabled`) and populates
        the menu with actions returned by :meth:`_get_file_menu_actions`.

        Override in subclasses to add extra logic (e.g., appending a
        submenu).  Call ``super()._update_file_menu()`` first to populate
        the default actions.
        """
        self.saveh5_action.setEnabled(self._is_save_enabled())
        add_actions(self.file_menu, self._get_file_menu_actions())
        if self.quit_action is not None:
            add_actions(self.file_menu, [self.quit_action])

    def _get_view_menu_actions(self) -> list[QW.QAction | None]:
        """Return the list of actions for the view menu.

        Override in subclasses to customize which actions appear.

        Returns:
            List of actions and separators
        """
        return [None] + self.createPopupMenu().actions()

    def _update_view_menu(self) -> None:
        """Update view menu before showing up.

        Override in subclasses to add extra logic.  Call
        ``super()._update_view_menu()`` first to populate the default
        actions.
        """
        add_actions(self.view_menu, self._get_view_menu_actions())

    def _get_help_doc_actions(self) -> list[QW.QAction | None]:
        """Return the documentation actions of the help menu.

        Override in subclasses to append application-specific entries such as
        a tour or a demo.

        Returns:
            List of actions and separators
        """
        actions: list[QW.QAction | None] = [
            create_action(
                self,
                _("Online documentation"),
                icon=get_icon("libre-gui-help.svg"),
                triggered=lambda: webbrowser.open(get_conf().app_docurl.get()),
            ),
        ]
        localdocpath = self.__get_local_doc_path()
        if localdocpath is not None:
            actions.append(
                create_action(
                    self,
                    _("PDF documentation"),
                    icon=get_icon("help_pdf.svg"),
                    triggered=lambda: webbrowser.open(localdocpath),
                ),
            )
        return actions

    def _get_help_support_actions(self) -> list[QW.QAction | None]:
        """Return the troubleshooting actions of the help menu.

        Override in subclasses to append application-specific entries such as
        an installation and configuration viewer.

        Returns:
            List of actions and separators
        """
        actions: list[QW.QAction | None] = []
        if TEST_SEGFAULT_ERROR:
            actions.append(
                create_action(
                    self,
                    _("Test segfault/Python error"),
                    triggered=self.test_segfault_error,
                )
            )
        actions.append(
            create_action(
                self,
                _("Log files") + "...",
                icon=get_icon("logs.svg"),
                triggered=self._show_logviewer,
            )
        )
        return actions

    def _get_help_about_actions(self) -> list[QW.QAction | None]:
        """Return the project and about actions of the help menu.

        Returns:
            List of actions and separators
        """
        return [
            None,
            create_action(
                self,
                _("Project home page"),
                icon=get_icon("libre-gui-globe.svg"),
                triggered=lambda: webbrowser.open(get_conf().app_homeurl.get()),
            ),
            create_action(
                self,
                _("Bug report or feature request"),
                icon=get_icon("libre-gui-globe.svg"),
                triggered=lambda: webbrowser.open(get_conf().app_supporturl.get()),
            ),
            create_action(
                self,
                _("About..."),
                icon=get_icon("libre-gui-about.svg"),
                triggered=self._about,
            ),
        ]

    def _get_help_menu_actions(self) -> list[QW.QAction | None]:
        """Return the list of actions for the help menu.

        Override in subclasses to wrap the standard groups, which are returned
        by :meth:`_get_help_doc_actions`, :meth:`_get_help_support_actions` and
        :meth:`_get_help_about_actions`.

        Returns:
            List of actions and separators
        """
        return (
            self._get_help_doc_actions()
            + self._get_help_support_actions()
            + self._get_help_about_actions()
        )

    @staticmethod
    def _check_h5file(filename: str, operation: str) -> str:
        """Check HDF5 filename"""
        filename = osp.abspath(osp.normpath(filename))
        bname = osp.basename(filename)
        if operation == "load" and not osp.isfile(filename):
            raise IOError(f'File not found "{bname}"')
        get_conf().base_dir.set(filename)
        return filename

    def _has_h5_workspace_persistence(self) -> bool:
        """Return whether the derived window implements workspace persistence."""
        return type(self).save_h5_workspace is not SGMXMainWindow.save_h5_workspace

    def save_to_h5_file(self, filename=None) -> None:
        """Save to a HDF5 file

        Args:
            filename: HDF5 filename. If None, a file dialog is opened.

        Raises:
            IOError: if filename is invalid or file cannot be saved.
        """
        if filename is None:
            basedir = get_conf().base_dir.get()
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
            h5files: HDF5 filenames (optionally with dataset name, separated by ",")
            import_all: Import all datasets from HDF5 files
            reset_all: Reset all application data before importing
        """
        if not self.confirm_memory_state():
            return
        conf = get_conf()
        if reset_all is None:
            # When workspace is empty, always preserve UUIDs (reset_all=True)
            # since there's no risk of conflicts
            reset_all = conf.h5_clear_workspace.get()
            if conf.h5_clear_workspace_ask.get():
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
                    conf.h5_clear_workspace_ask.set(False)
        if h5files is None:
            basedir = conf.base_dir.get()
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
                    filename = self._check_h5file(filename, "load")
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
        self, filenames: list[str], reset_all: bool | None = None
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
            reset_all: Reset all application data before importing (unused)
        """
        del reset_all
        for filename in filenames:
            self._check_h5file(filename, "load")

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

        Subclasses that manage a data model must override this method to
        perform the actual serialization (e.g. using
        :class:`guidata.io.HDF5Writer`). The base implementation never clears
        the modified state because it cannot persist an application workspace.

        Args:
            filename: HDF5 filename to save to

        Raises:
            NotImplementedError: Always, because the base window has no
             application workspace to serialize.
        """
        del filename
        raise NotImplementedError(
            "Override save_h5_workspace() to serialize the application workspace."
        )

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
            filename = self._check_h5file(filename, "load")
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

    def reset_all(self) -> None:
        """Reset all application data.

        The base implementation is a **no-op**.  Subclasses should override
        this method to clear their data model (e.g. remove all objects
        from panels).
        """

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
        conf = get_conf()
        app_name = conf.app_name.get()
        app_version = conf.app_version.get()
        app_desc = conf.app_desc.get()
        app_homeurl = conf.app_homeurl.get()
        app_docurl = conf.app_docurl.get()
        app_supporturl = conf.app_supporturl.get()
        dev_by = conf.app_developer.get()
        cprght = conf.app_copyright.get()

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
                f'<p>Based on <a href="{__homeurl__}">{MOD_TITLE}</a> v{__version__}',
                f"<br>{MOD_DESC}",
                f"<br>{sgmx_dev_by}",
                f"<br>Copyright &copy; {sgmx_cprght}",
            ]
        )

        QW.QMessageBox.about(
            self,
            _("About") + " " + app_name,
            "".join(about_parts),
        )

    def _update_color_mode(self, startup: bool = False) -> None:
        """Update color mode

        Args:
            startup: True if method is called during application startup (in that case,
             color theme is applied only if mode != "auto")
        """
        mode = get_conf().color_mode.get()
        if startup and mode == "auto":
            guidata_qth.win32_fix_title_bar_background(self)
            return

        # Prevent Qt from refreshing the window when changing the color mode:
        self.setUpdatesEnabled(False)

        plotpy_config.set_plotpy_color_mode(mode)
        get_conf().apply_plotpy_defaults()

        if self.console is not None:
            self.console.update_color_mode()

        if self.docks is not None:
            for dock in self.docks.values():
                widget = dock.widget()
                if isinstance(widget, DockablePlotWidget):
                    widget.update_color_mode()

        self._update_extra_color_mode()

        # Allow Qt to refresh the window:
        self.setUpdatesEnabled(True)

    def _update_extra_color_mode(self) -> None:
        """Update the color mode of application-specific widgets.

        Called with window updates disabled, after the console and the plot docks
        have been updated. The base implementation is a no-op.
        """

    def _show_logviewer(self) -> None:
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
    def _get_save_before_quit_message(self) -> str:
        """Return the confirmation message shown before closing modified data."""
        return _(
            "Do you want to save all signals and images "
            "to an HDF5 file before quitting the application?"
        )

    def _close_managed_widgets(self) -> None:
        """Close widgets owned by the generic application shell."""
        if self.console is not None:
            try:
                self.console.close()
            except RuntimeError:
                # The Qt object may already be deleted when restarting a window
                # in the same test process.
                pass

    def _cleanup_before_reset(self) -> None:
        """Clean up derived services before resetting application data."""

    def _cleanup_after_state_save(self) -> None:
        """Finalize derived shutdown after saving the window state."""

    def close_properly(self) -> bool:
        """Close properly

        Returns:
            True if closed properly, False otherwise
        """
        if not execenv.unattended and self.is_modified():
            answer = QW.QMessageBox.warning(
                self,
                _("Quit"),
                self._get_save_before_quit_message(),
                QW.QMessageBox.Yes | QW.QMessageBox.No | QW.QMessageBox.Cancel,
            )
            if answer == QW.QMessageBox.Yes:
                self.save_to_h5_file()
                if self.is_modified():
                    return False
            elif answer == QW.QMessageBox.Cancel:
                return False
        self.hide()  # Avoid showing individual widgets closing one after the other
        self._close_managed_widgets()
        self._cleanup_before_reset()
        self.reset_all()
        self._save_pos_size_and_state()
        self._cleanup_after_state_save()

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
