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
from guidata.qthelpers import add_actions, create_action
from guidata.widgets.console import DockableConsole
from plotpy import config as plotpy_config

# from plotpy.builder import make
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

# from qtpy.compat import getopenfilenames, getsavefilename
from sigima.objects import ImageObj, SignalObj, create_image, create_signal

import sigimax
from sigimax import __docurl__, __homeurl__, __supporturl__, env
from sigimax.config import (
    APP_DESC,
    APP_NAME,
    DATAPATH,
    DEBUG,
    TEST_SEGFAULT_ERROR,
    Conf,
    _,
)
from sigimax.env import execenv
from sigimax.gui.actionhandler import ActionCategory
from sigimax.gui.docks import DockablePlotWidget
from sigimax.utils import qthelpers as qth
from sigimax.utils.qthelpers import (
    # add_corner_menu,
    bring_to_front,
    configure_menu_about_to_show,
)
from sigimax.widgets import logviewer, status
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
        self.setObjectName(APP_NAME)
        # TODO by config option -> set AppIcon (generic) + set default
        # self.setWindowIcon(get_icon("DataLab.svg"))

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
        self.autorefresh_action: QW.QAction | None = None
        self.showfirstonly_action: QW.QAction | None = None
        self.showlabel_action: QW.QAction | None = None

        self.file_menu: QW.QMenu | None = None
        self.create_menu: QW.QMenu | None = None
        self.edit_menu: QW.QMenu | None = None
        # TODO : check if we kept operation, processing and analysis menus in SigimaX
        self.operation_menu: QW.QMenu | None = None
        self.processing_menu: QW.QMenu | None = None
        self.analysis_menu: QW.QMenu | None = None
        self.view_menu: QW.QMenu | None = None
        self.help_menu: QW.QMenu | None = None

        self.__update_color_mode(startup=True)

        self.__is_modified = False
        self.set_modified(False)

        # Setup actions and menus
        if console is None:
            console = Conf.console.console_enabled.get()
        self.setup(console)

        self.__restore_pos_and_size()
        execenv.log(self, "Initialization done")

    # ------Misc.
    @property
    def panels(
        self,
    ) -> (
        tuple
    ):  # TODO check extract Panel (abstract and base)// tuple[AbstractPanel, ...]:
        """Return the tuple of implemented panels (signal, image)

        Returns:
            Tuple of panels
        """
        # return (self.signalpanel, self.imagepanel, self.macropanel)
        return ()

    def __set_low_memory_state(self, state: bool) -> None:
        """Set memory warning state"""
        self.__memory_warning = state

    def confirm_memory_state(self) -> bool:  # pragma: no cover
        """Check memory warning state and eventually show a warning dialog

        Returns:
            True if memory state is ok
        """
        if not env.execenv.unattended and self.__memory_warning:
            threshold = Conf.main.available_memory_threshold.get()
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
            f"<b>{APP_NAME}</b> v{sigimax.__version__}:",
            "",
            _("<i>This is not a stable release.</i>"),
            "",
            rel,
        ]
        if not env.execenv.unattended:
            QW.QMessageBox.warning(
                self, APP_NAME, "<br>".join(txtlist), QW.QMessageBox.Ok
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
        elif Conf.main.faulthandler_log_available.get(
            False
        ) or Conf.main.traceback_log_available.get(False):
            txt = "<br>".join(
                [
                    logviewer.get_log_prompt_message(),
                    "",
                    _("Do you want to see available log files?"),
                ]
            )
            btns = QW.QMessageBox.StandardButton.Yes | QW.QMessageBox.StandardButton.No
            choice = QW.QMessageBox.warning(self, APP_NAME, txt, btns)
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
        return
        # for panel in self.panels:
        # TODO check extract BasePanel and AbstractPanel
        # if isinstance(panel, base.BaseDataPanel):
        #    self.tabwidget.setCurrentWidget(panel)
        #    for name in (
        #        "file",
        #        "create",
        #        "edit",
        #        "roi",
        #        "view",
        #        "operation",
        #        "processing",
        #        "analysis",
        #        "help",
        #    ):
        #        menu = getattr(self, f"{name}_menu")
        #        menu.popup(self.pos())
        #        qth.grab_save_window(menu, f"{panel.objectName()}_{name}")
        #        menu.close()
        # TODO check extract BasePanel and AbstractPanel
        # if panel in (self.signalpanel, self.imagepanel):
        #    panel: BaseDataPanel
        #    # Take screenshots of Edit menu submenus (Metadata and Annotations)
        #    for submenu, suffix in (
        #        (panel.acthandler.metadata_submenu, "_edit_metadata"),
        #        (panel.acthandler.annotations_submenu, "_edit_annotations"),
        #    ):
        #        submenu.popup(self.pos())
        #        qth.grab_save_window(submenu, f"{panel.objectName()}{suffix}")
        #        submenu.close()

    # ------GUI setup
    def __restore_pos_and_size(self) -> None:
        """Restore main window position and size from configuration"""
        pos = Conf.main.window_position.get(None)
        if pos is not None:
            posx, posy = pos
            self.move(QC.QPoint(posx, posy))
        size = Conf.main.window_size.get(None)
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
        state = Conf.main.window_state.get(None)
        if state is not None:
            state = base64.b64decode(state)
            self.restoreState(QC.QByteArray(state))
            for widget in self.children():
                if isinstance(widget, QW.QDockWidget):
                    self.restoreDockWidget(widget)

    def __save_pos_size_and_state(self) -> None:
        """Save main window position, size and state to configuration"""
        is_maximized = self.windowState() == QC.Qt.WindowMaximized
        Conf.main.window_maximized.set(is_maximized)
        if not is_maximized:
            size = self.size()
            Conf.main.window_size.set((size.width(), size.height()))
            pos = self.pos()
            Conf.main.window_position.set((pos.x(), pos.y()))
        # Encoding window state into base64 string to avoid sending binary data
        # to the configuration file:
        state = base64.b64encode(self.saveState().data()).decode("ascii")
        Conf.main.window_state.set(state)

    def setup(self, console: bool = False) -> None:
        """Setup main window

        Args:
            console: True to setup console
        """
        self.__configure_statusbar(console)
        self.__setup_global_actions()
        # self.__add_signal_image_panels()
        self.__setup_central_widget()
        self.__add_menus()
        if console:
            self.__setup_console()
        self.__update_actions(update_other_data_panel=True)
        # self.__add_macro_panel()
        self.__configure_panels()
        # Now that everything is set up, we can restore the window state:
        self.__restore_state()

    def __configure_statusbar(self, console: bool) -> None:
        """Configure status bar

        Args:
            console: True if console is enabled
        """
        self.statusBar().showMessage(_("Welcome to %s!") % APP_NAME, 5000)
        if console:
            # Console status
            self.consolestatus = status.ConsoleStatus()
            self.statusBar().addPermanentWidget(self.consolestatus)
        # Memory status
        threshold = Conf.main.available_memory_threshold.get()
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
        # View menu actions
        self.autorefresh_action = create_action(
            self,
            _("Auto-refresh"),
            icon=get_icon("refresh-auto.svg"),
            tip=_("Auto-refresh plot when object is modified, added or removed"),
            toggled=self.handle_autorefresh_action,
        )
        # TODO check if it's generic
        # self.showfirstonly_action = create_action(
        #    self,
        #    _("Show first object only"),
        #    icon=get_icon("show_first.svg"),
        #    tip=_("Show only the first selected object (signal or image)"),
        #    toggled=self.toggle_show_first_only,
        # )
        # self.showlabel_action = create_action(
        #    self,
        #    _("Show graphical object titles"),
        #    icon=get_icon("show_titles.svg"),
        #    tip=_("Show or hide ROI and other graphical object titles or subtitles"),
        #    toggled=self.toggle_show_titles,
        # )

    def __setup_central_widget(self) -> None:
        """Setup central widget (main panel)"""
        # TODO check extract BasePanel and AbstractPanel
        # self.tabwidget.setMaximumWidth(600)
        # s_idx = self.tabwidget.addTab(
        #    self.signalpanel, get_icon("signal.svg"), _("Signal Panel")
        # )
        # i_idx = self.tabwidget.addTab(
        #    self.imagepanel, get_icon("image.svg"), _("Image Panel")
        # )
        # self.tabwidget.setTabToolTip(
        #    s_idx, _("1D Signals: Manage and process one-dimensional data")
        # )
        # self.tabwidget.setTabToolTip(
        #    i_idx, _("2D Images: Manage and process two-dimensional data")
        # )

        # Apply enhanced tab bar styling
        tab_bar = self.tabwidget.tabBar()
        font = tab_bar.font()
        font.setPointSize(10)
        tab_bar.setFont(font)
        # Use QTimer to ensure tab bar is properly sized first
        QC.QTimer.singleShot(0, self.__update_tab_icon_size)

        self.setCentralWidget(self.tabwidget)

    def __update_tab_icon_size(self) -> None:
        """Update tab icon size based on tab bar height"""
        tab_bar = self.tabwidget.tabBar()
        if tab_bar.height() > 0:
            # Use approximately 80% of tab height for icon size
            icon_size = int(tab_bar.height() * 0.8)
            self.tabwidget.setIconSize(QC.QSize(icon_size, icon_size))

    @staticmethod
    def __get_local_doc_path() -> str | None:
        """Return local documentation path, if it exists"""
        locale = QC.QLocale.system().name()
        for suffix in ("_" + locale[:2], "_en"):
            path = osp.join(DATAPATH, "doc", f"{APP_NAME}{suffix}.pdf")
            if osp.isfile(path):
                return path
        return None

    def __add_menus(self) -> None:
        """Adding menus"""
        self.file_menu = self.menuBar().addMenu(_("&File"))
        configure_menu_about_to_show(self.file_menu, self.__update_file_menu)
        self.create_menu = self.menuBar().addMenu(_("&Create"))
        self.edit_menu = self.menuBar().addMenu(_("&Edit"))
        # TODO : check if we keep operation, processing and analysis menus in SigimaX
        self.operation_menu = self.menuBar().addMenu(_("Operations"))
        self.processing_menu = self.menuBar().addMenu(_("Processing"))
        self.analysis_menu = self.menuBar().addMenu(_("Analysis"))
        self.view_menu = self.menuBar().addMenu(_("&View"))
        configure_menu_about_to_show(self.view_menu, self.__update_view_menu)
        self.help_menu = self.menuBar().addMenu("?")
        for menu in (
            self.create_menu,
            self.edit_menu,
            self.operation_menu,
            self.processing_menu,
            self.analysis_menu,
        ):
            configure_menu_about_to_show(menu, self.__update_generic_menu)
        help_menu_actions = [
            create_action(
                self,
                _("Online documentation"),
                icon=get_icon("libre-gui-help.svg"),
                triggered=lambda: webbrowser.open(__docurl__),
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
                triggered=lambda: webbrowser.open(__homeurl__),
            ),
            create_action(
                self,
                _("Bug report or feature request"),
                icon=get_icon("libre-gui-globe.svg"),
                triggered=lambda: webbrowser.open(__supporturl__),
            ),
            create_action(
                self,
                _("About..."),
                icon=get_icon("libre-gui-about.svg"),
                triggered=self.__about,
            ),
        ]
        add_actions(self.help_menu, help_menu_actions)

    def __update_console_show_mode(self) -> None:
        """Update console show mode from configuration option

        Console show mode is whether the console is shown or not when an error occurs.
        """
        if self.console is not None:
            state = Conf.console.show_console_on_error.get()
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
        self.console.setMaximumBlockCount(Conf.console.max_line_count.get(5000))
        self.console.go_to_error.connect(go_to_error)
        cdock = self.__add_dockwidget(self.console, _("Console"))
        self.docks[self.console] = cdock
        cdock.hide()
        self.console.interpreter.widget_proxy.sig_new_prompt.connect(
            lambda txt: self.repopulate_panel_trees()
        )
        self.__update_console_show_mode()
        self.console.exception_occurred.connect(self.consolestatus.exception_occurred)
        cdock.visibilityChanged.connect(self.consolestatus.console_visibility_changed)
        self.consolestatus.SIG_SHOW_CONSOLE.connect(self.console.show_console)

    def __configure_panels(self) -> None:
        """Configure panels"""
        # Connectings signals
        for panel in self.panels:
            panel.SIG_OBJECT_ADDED.connect(self.set_modified)
            panel.SIG_OBJECT_REMOVED.connect(self.set_modified)
        self.macropanel.SIG_OBJECT_MODIFIED.connect(self.set_modified)
        # Initializing common panel actions
        self.autorefresh_action.setChecked(Conf.view.auto_refresh.get(True))
        self.showfirstonly_action.setChecked(Conf.view.show_first_only.get(False))
        self.showlabel_action.setChecked(Conf.view.show_label.get(False))
        # Restoring current tab from last session
        tab_idx = Conf.main.current_tab.get(None)
        if tab_idx is not None:
            self.tabwidget.setCurrentIndex(tab_idx)
        # Set focus on current panel, so that keyboard shortcuts work (Fixes #10)
        self.tabwidget.currentWidget().setFocus()

    # TODO check extract BasePanel and AbstractPanel + no processor in SigimaX
    # def set_process_isolation_enabled(self, state: bool) -> None:
    #    """Enable/disable process isolation
    #
    #    Args:
    #        state: True to enable process isolation
    #    """
    #    for processor in (self.imagepanel.processor, self.signalpanel.processor):
    #        processor.set_process_isolation_enabled(state)

    # ------GUI refresh
    def has_objects(self) -> bool:
        """Return True if sig/ima panels have any object"""
        return sum(len(panel) for panel in self.panels) > 0

    def set_modified(self, state: bool = True) -> None:
        """Set mainwindow modified state"""
        state = state and self.has_objects()
        self.__is_modified = state
        title = APP_NAME + ("*" if state else "")
        if not sigimax.__version__.replace(".", "").isdigit():
            title += f" [{sigimax.__version__}]"
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

    def repopulate_panel_trees(self) -> None:
        """Repopulate all panel trees"""
        # TODO check extract BasePanel and AbstractPanel
        # for panel in self.panels:
        #    if isinstance(panel, base.BaseDataPanel):
        #        panel.objview.populate_tree()

    def __update_actions(self, update_other_data_panel: bool = False) -> None:
        """Update selection dependent actions

        Args:
            update_other_data_panel: True to update other data panel actions
             (i.e. if the current panel is the signal panel, also update the image
             panel actions, and vice-versa)
        """
        # TODO check extract BasePanel and AbstractPanel
        # is_signal = self.tabwidget.currentWidget() is self.signalpanel
        # panel = self.signalpanel if is_signal else self.imagepanel
        # other_panel = self.imagepanel if is_signal else self.signalpanel
        # if update_other_data_panel:
        #    other_panel.selection_changed()
        # panel.selection_changed()
        # self.signalpanel_toolbar.setVisible(is_signal)
        # self.imagepanel_toolbar.setVisible(not is_signal)

    def __update_generic_menu(self, menu: QW.QMenu | None = None) -> None:
        """Update menu before showing up -- Generic method"""
        if menu is None:
            menu = self.sender()
        menu.clear()
        panel = self.tabwidget.currentWidget()
        category = {
            self.file_menu: ActionCategory.FILE,
            self.create_menu: ActionCategory.CREATE,
            self.edit_menu: ActionCategory.EDIT,
            self.view_menu: ActionCategory.VIEW,
            self.operation_menu: ActionCategory.OPERATION,
            self.processing_menu: ActionCategory.PROCESSING,
            self.analysis_menu: ActionCategory.ANALYSIS,
        }[menu]
        actions = panel.get_category_actions(category)
        add_actions(menu, actions)

    def __update_file_menu(self) -> None:
        """Update file menu before showing up"""
        self.saveh5_action.setEnabled(self.has_objects())
        self.__update_generic_menu(self.file_menu)
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
        self.__update_generic_menu(self.view_menu)
        add_actions(self.view_menu, [None] + self.createPopupMenu().actions())

    def handle_autorefresh_action(self, state: bool) -> None:
        """Handle auto-refresh action from UI (with confirmation dialog)

        Args:
            state: desired state
        """
        # If disabling auto-refresh, show confirmation dialog
        if not state:
            txtlist = [
                "<b>" + _("Disable auto-refresh?") + "</b>",
                "",
                _(
                    "When auto-refresh is disabled, the plot view will not "
                    "automatically update when objects are modified, added or removed."
                ),
                "",
                _(
                    "You will need to manually click the refresh button to update "
                    "the view."
                ),
                "",
                _("Are you sure you want to disable auto-refresh?"),
            ]

            answer = QW.QMessageBox.question(
                self,
                APP_NAME,
                "<br>".join(txtlist),
                QW.QMessageBox.Yes | QW.QMessageBox.No,
                QW.QMessageBox.No,
            )

            if answer == QW.QMessageBox.No:
                # User cancelled, restore the action's checked state
                self.autorefresh_action.blockSignals(True)
                self.autorefresh_action.setChecked(True)
                self.autorefresh_action.blockSignals(False)
                return

        # Apply the change
        self.toggle_auto_refresh(state)

    # This method is intentionally *not* remote controlled
    # (see TODO regarding RemoteClient.add_object method)
    #  @remote_controlled
    def add_object(
        self, obj: SignalObj | ImageObj, group_id: str = "", set_current=True
    ) -> None:
        """Add object - signal or image

        Args:
            obj: object to add (signal or image)
            group_id: group ID (optional)
            set_current: True to set the object as current object
        """
        # TODO check extract BasePanel and AbstractPanel and if we keep it in SigimaX
        # if self.confirm_memory_state():
        #    if isinstance(obj, SignalObj):
        #        self.signalpanel.add_object(obj, group_id, set_current)
        #    elif isinstance(obj, ImageObj):
        #        self.imagepanel.add_object(obj, group_id, set_current)
        #    else:
        #        raise TypeError(f"Unsupported object type {type(obj)}")

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

    def add_signal(
        self,
        title: str,
        xdata: np.ndarray,
        ydata: np.ndarray,
        xunit: str = "",
        yunit: str = "",
        xlabel: str = "",
        ylabel: str = "",
        group_id: str = "",
        set_current: bool = True,
    ) -> bool:  # pylint: disable=too-many-arguments
        """Add signal data to SigimaX main application.

        Args:
            title: Signal title
            xdata: X data
            ydata: Y data
            xunit: X unit. Defaults to ""
            yunit: Y unit. Defaults to ""
            xlabel: X label. Defaults to ""
            ylabel: Y label. Defaults to ""
            group_id: group id in which to add the signal. Defaults to ""
            set_current: if True, set the added signal as current

        Returns:
            True if signal was added successfully, False otherwise

        Raises:
            ValueError: Invalid xdata dtype
            ValueError: Invalid ydata dtype
        """
        obj = create_signal(
            title,
            xdata,
            ydata,
            units=(xunit, yunit),
            labels=(xlabel, ylabel),
        )
        self.add_object(obj, group_id, set_current)
        return True

    def add_image(
        self,
        title: str,
        data: np.ndarray,
        xunit: str = "",
        yunit: str = "",
        zunit: str = "",
        xlabel: str = "",
        ylabel: str = "",
        zlabel: str = "",
        group_id: str = "",
        set_current: bool = True,
    ) -> bool:  # pylint: disable=too-many-arguments
        """Add image data to SigimaX main application.

        Args:
            title: Image title
            data: Image data
            xunit: X unit. Defaults to ""
            yunit: Y unit. Defaults to ""
            zunit: Z unit. Defaults to ""
            xlabel: X label. Defaults to ""
            ylabel: Y label. Defaults to ""
            zlabel: Z label. Defaults to ""
            group_id: group id in which to add the image. Defaults to ""
            set_current: if True, set the added image as current

        Returns:
            True if image was added successfully, False otherwise

        Raises:
            ValueError: Invalid data dtype
        """
        obj = create_image(
            title,
            data,
            units=(xunit, yunit, zunit),
            labels=(xlabel, ylabel, zlabel),
        )
        self.add_object(obj, group_id, set_current)
        return True

    # ------?
    def __about(self) -> None:  # pragma: no cover
        """About dialog box"""
        self.check_stable_release()
        if Conf.main.process_isolation_enabled.get():
            pistate = "<font color='green'>" + _("enabled") + "</font>"
        else:
            pistate = "<font color='red'>" + _("disabled") + "</font>"
        adv_conf = "<br>".join(
            [
                "<i>" + _("Advanced configuration:") + "</i>",
                "• " + _("Process isolation:") + " " + pistate,
            ]
        )
        # TODO implement "about" configuration in SigimaX
        created_by = _("Created by")
        dev_by = _("Developed and maintained by %s open-source project team") % APP_NAME
        cprght = "2023 DataLab Platform Developers"
        QW.QMessageBox.about(
            self,
            _("About") + " " + APP_NAME,
            f"""<b>{APP_NAME}</b> v{sigimax.__version__}<br>{APP_DESC}
              <p>{created_by} Pierre Raybaut<br>{dev_by}<br>Copyright &copy; {cprght}
              <p>{adv_conf}""",
        )

    def __update_color_mode(self, startup: bool = False) -> None:
        """Update color mode

        Args:
            startup: True if method is called during application startup (in that case,
             color theme is applied only if mode != "auto")
        """
        mode = Conf.main.color_mode.get()
        if startup and mode == "auto":
            guidata_qth.win32_fix_title_bar_background(self)
            return

        # Prevent Qt from refreshing the window when changing the color mode:
        self.setUpdatesEnabled(False)

        plotpy_config.set_plotpy_color_mode(mode)

        if self.console is not None:
            self.console.update_color_mode()
        # TODO check extract BasePanel and AbstractPanel
        # if self.macropanel is not None:
        #    self.macropanel.update_color_mode()
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
        for panel in self.panels:
            if panel is not None:
                panel.close()
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
        Conf.main.current_tab.set(self.tabwidget.currentIndex())

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
