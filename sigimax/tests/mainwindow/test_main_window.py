# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Application test for main window
--------------------------------

Testing the features of the main window of the application that are not
covered by other tests.
"""

# guitest: show

import pytest
from plotpy.constants import PlotType

from sigimax.tests import sigimax_test_app_context
from sigimax.widgets.h5browser import H5Browser
from sigimax.widgets.plotdock import DockablePlotWidget


@pytest.mark.app
def test_main_app():
    """Main window test"""
    with sigimax_test_app_context(console=True) as win:
        print("Main window test")
        win.activateWindow()

        # Add two DockablePlotWidget docks
        for title, plot_type in (
            ("Curve Plot", PlotType.CURVE),
            ("Image Plot", PlotType.IMAGE),
        ):
            dock_widget = DockablePlotWidget(win, plot_type)
            dockwidget, location = dock_widget.create_dockwidget(title)
            win.addDockWidget(location, dockwidget)
            win.docks[dock_widget] = dockwidget

        # central_widget = SigimaXPlotWidget(plot_type=PlotType.CURVE)
        central_widget = H5Browser()
        win.setCentralWidget(central_widget)
        # win.removeToolBar(win.main_toolbar)  # Remove the default toolbar
        # win.statusBar().hide()  # Hide the status bar
        # win.menuBar().hide()  # Hide the menu bar


if __name__ == "__main__":
    test_main_app()
