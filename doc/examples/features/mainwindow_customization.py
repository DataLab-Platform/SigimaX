# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Main Window Customization
============================

:class:`~sigimax.mainwindow.SGMXMainWindow` is designed to be subclassed, not
configured. This example walks through the four extension points a derived
application typically overrides, in isolation:

1. **Docks** — :meth:`~sigimax.mainwindow.SGMXMainWindow._setup_docks`
2. **Menu layout** — :meth:`~sigimax.mainwindow.SGMXMainWindow._get_menubar_layout`
3. **Actions** — populating menus (custom and standard) with
   :func:`guidata.qthelpers.create_action`/:func:`guidata.qthelpers.add_actions`
4. **Status bar** — :meth:`~sigimax.mainwindow.SGMXMainWindow._get_extra_status_widgets`

See :doc:`../use_cases/full_app` for a complete application built the same way.
"""

# %%
# Importing necessary modules
# ---------------------------

from guidata.configtools import get_icon
from guidata.qthelpers import add_actions, create_action
from plotpy.constants import PlotType
from qtpy import QtWidgets as QW

from sigimax.config import CONF as Conf
from sigimax.config import _
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils.qthelpers import sigimax_app_context
from sigimax.widgets.plotdock import DockablePlotWidget

# %%
# Custom main window
# ---------------------
#
# Each extension point below is independent: override only the ones your
# application needs.


class MyAppMainWindow(SGMXMainWindow):
    """Main window demonstrating docks, menus, actions and status bar."""

    def __init__(self, console=None, hide_on_close=False):
        Conf.app_name.set("CustomizedApp")
        self.curve_dock = None
        self.task_status = None
        super().__init__(console=console, hide_on_close=hide_on_close)

    # -- 1. Docks --------------------------------------------------------

    def _setup_docks(self):
        """Add a business-specific dock (a dockable curve plot, here)."""
        self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
        self._add_dockwidget(self.curve_dock, _("Signal Viewer"), name="signal_viewer")

    # -- 2. Menu layout ----------------------------------------------------
    #
    # The base layout is ``[("file", "&File"), ("view", "&View"), ("help", "?")]``.
    # Insert your own entries while keeping the ones the base class relies on
    # (``file_menu``/``view_menu``/``help_menu`` are used internally).

    def _get_menubar_layout(self):
        base_layout = super()._get_menubar_layout()
        # Insert "Analysis" between "File" and "View"
        return [base_layout[0], ("analysis", _("&Analysis")), *base_layout[1:]]

    # -- 3. Actions ----------------------------------------------------------
    #
    # ``_post_setup`` runs once menus, docks and the console all exist, so
    # it is the right place to populate both custom and standard menus.

    def _post_setup(self, console):
        # Populate our own menu (created from the layout above as `self.analysis_menu`)
        add_actions(
            self.analysis_menu,
            [
                create_action(
                    self,
                    _("Run analysis"),
                    icon=get_icon("libre-gui-check.svg"),
                    triggered=self._run_analysis,
                ),
            ],
        )
        # Add an action to a *standard* menu created by the base class
        add_actions(
            self.file_menu,
            [
                create_action(
                    self,
                    _("Export report..."),
                    triggered=self._export_report,
                ),
            ],
        )

    def _run_analysis(self):
        self.statusBar().showMessage(_("Running analysis..."), 2000)

    def _export_report(self):
        self.statusBar().showMessage(_("Exporting report..."), 2000)

    # -- 4. Status bar --------------------------------------------------------
    #
    # Widgets returned here are inserted between the console status (if any)
    # and the built-in memory status widget.

    def _get_extra_status_widgets(self):
        self.task_status = QW.QLabel(_("Idle"))
        return [self.task_status]


# %%
# Instantiating the window
# ---------------------------

with sigimax_app_context(exec_loop=False):
    win = MyAppMainWindow(console=False)
    win.resize(900, 600)
    win.show()

    print(f"Menu titles: {[a.text() for a in win.menuBar().actions()]}")
    print(f"Analysis menu actions: {[a.text() for a in win.analysis_menu.actions()]}")
    print(f"Extra status widgets: {win.task_status.text()}")

    win.close()

# %%
# Summary
# -------
#
# - ``_setup_docks`` / ``_get_menubar_layout`` / ``_get_extra_status_widgets``
#   return declarative descriptions consumed by the base class — override
#   them instead of poking at Qt internals
# - ``_post_setup`` is where menus (custom or standard) get their actions,
#   once everything else is guaranteed to exist
# - Standard menus (``file_menu``, ``view_menu``, ``help_menu``) remain
#   available for derived applications to extend, not just replace
