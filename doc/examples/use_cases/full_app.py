# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Full Derived Application
=========================

This use case demonstrates a complete derived application built on SigimaX,
showcasing:

- Custom configuration with typed options
- Custom main window with menus, toolbars, and dock widgets
- Interactive curve generation using PlotPy
- Configuration display via console

This example mirrors the derivation pattern used by
`DataLab <https://datalab-platform.com/>`_ — the flagship application built
on SigimaX.
"""

# %%
# Importing necessary modules
# ---------------------------

import numpy as np
from guidata.configtools import get_icon
from guidata.qthelpers import add_actions, create_action
from plotpy.builder import make
from plotpy.constants import PlotType
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from sigimax.app import create as sigimax_create
from sigimax.config import CONF as Conf
from sigimax.config import EnumOptionField, SigimaXOptions, TypedOptionField, _
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils.qthelpers import sigimax_app_context
from sigimax.widgets.plotdock import DockablePlotWidget

# %%
# Step 1: Define the application configuration
# ----------------------------------------------
#
# Custom options extend :class:`~sigimax.config.SigimaXOptions` with
# domain-specific settings.


class SciAppOptions(SigimaXOptions):
    """Configuration for a scientific analysis application."""

    def __init__(self):
        super().__init__()
        self.app_name.set("SciApp")
        self.app_version.set("1.0.0")
        self.app_desc.set("Scientific analysis app built on SigimaX")

        self.sample_rate = TypedOptionField(
            self,
            "sample_rate",
            default=1000,
            expected_type=int,
            description="Default sampling rate (Hz)",
        )
        self.signal_type = EnumOptionField(
            self,
            "signal_type",
            default="sine",
            choices=["sine", "square", "sawtooth", "noise"],
            description="Default signal type for generation",
        )


# %%
# Step 2: Build the custom main window
# --------------------------------------
#
# Override :class:`~sigimax.mainwindow.SGMXMainWindow` to add domain-specific
# menus, toolbars, and dock widgets.


class SciAppMainWindow(SGMXMainWindow):
    """Main window for the SciApp analysis application."""

    def __init__(self, console=None, hide_on_close=False):
        Conf.app_name.set("SciApp")
        Conf.app_version.set("1.0.0")
        self.curve_dock = None
        super().__init__(console=console, hide_on_close=hide_on_close)

    def _setup_docks(self):
        """Add the dockable curve plot."""
        self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
        self._add_dockwidget(self.curve_dock, _("Signal Viewer"), name="signal_viewer")

    def _post_setup(self, console):
        """Add custom menus and toolbar."""
        self._setup_analysis_menu()
        self._setup_toolbar()

    def _setup_analysis_menu(self):
        """Add a custom Analysis menu."""
        menu = self.menuBar().addMenu(_("&Analysis"))
        add_actions(
            menu,
            [
                create_action(
                    self,
                    _("Generate signal"),
                    icon=get_icon("new_signal.svg"),
                    triggered=self._generate_signal,
                ),
                create_action(
                    self,
                    _("Clear plot"),
                    icon=get_icon("libre-gui-close.svg"),
                    triggered=self._clear_plot,
                ),
            ],
        )

    def _setup_toolbar(self):
        """Add a quick-access toolbar."""
        toolbar = QW.QToolBar(_("Analysis"), self)
        toolbar.setObjectName("analysis_toolbar")
        self.addToolBar(QC.Qt.TopToolBarArea, toolbar)
        toolbar.addAction(
            create_action(
                self,
                _("Generate"),
                icon=get_icon("new_signal.svg"),
                triggered=self._generate_signal,
            )
        )

    def _generate_signal(self):
        """Generate a test signal and add it to the plot."""
        t = np.linspace(0, 1, 1000)
        y = np.sin(2 * np.pi * 5 * t) + 0.3 * np.random.randn(len(t))
        plot = self.curve_dock.get_plot()
        plot.add_item(make.curve(t, y, title="Signal", color="blue"))
        plot.do_autoscale()
        self.statusBar().showMessage(_("Signal generated"), 3000)

    def _clear_plot(self):
        """Clear all items from the plot."""
        plot = self.curve_dock.get_plot()
        plot.del_all_items()
        plot.replot()


# %%
# Step 3: Launch and demonstrate
# --------------------------------

with sigimax_app_context(exec_loop=False):
    win = sigimax_create(
        window_class=SciAppMainWindow,
        splash=False,
        console=False,
        size=(1000, 650),
    )
    win.show()

    # Generate a signal to demonstrate
    win._generate_signal()  # noqa: SLF001

    print(f"Application: {Conf.app_name.get()}")
    print(f"Window title: {win.windowTitle()}")
    print(f"Plot items: {len(win.curve_dock.get_plot().get_items())}")

    win.set_modified(False)
    win.close()

# %%
# Summary
# -------
#
# This example demonstrated a complete SigimaX-based application with:
#
# - **Custom configuration** (``SciAppOptions``) with typed fields
# - **Custom main window** (``SciAppMainWindow``) with Analysis menu and toolbar
# - **Interactive plot** via ``DockablePlotWidget``
# - **Status bar** messages on user actions
#
# For a standalone application, replace the ``create()`` call with
# ``run(window_class=SciAppMainWindow, console=True)`` to enter the Qt event loop.
