# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Dockable Plot Widget
====================

This example demonstrates how to use the :class:`~sigimax.widgets.plotdock.DockablePlotWidget`
to embed interactive PlotPy curve and image plots in dock widgets.

The ``DockablePlotWidget`` is a key building block for SigimaX-based applications,
providing:

- Embedding of PlotPy ``CurvePlot`` or ``ImagePlot`` in a Qt dock widget
- Configurable dock location (left, right, top, bottom)
- Optional watermark image
- Automatic integration with the main window's dock system
"""

# %%
# Importing necessary modules
# ---------------------------

import numpy as np
from plotpy.builder import make
from plotpy.constants import PlotType
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from sigimax.utils.qthelpers import sigimax_app_context
from sigimax.widgets.plotdock import DockablePlotWidget

# %%
# Creating a curve plot widget
# -----------------------------
#
# The simplest usage: create a ``DockablePlotWidget`` with ``PlotType.CURVE``
# and add some curves using PlotPy's builder.

with sigimax_app_context(exec_loop=False):
    # Create a main window to host the dock
    main = QW.QMainWindow()
    main.setWindowTitle("DockablePlotWidget Demo")
    main.resize(800, 500)

    # Create a dockable curve plot
    curve_widget = DockablePlotWidget(main, PlotType.CURVE)
    dock, location = curve_widget.create_dockwidget("Curve Plot")
    main.addDockWidget(location, dock)

    # Add some curves
    x = np.linspace(0, 4 * np.pi, 500)
    plot = curve_widget.get_plot()
    plot.add_item(make.curve(x, np.sin(x), title="sin(x)", color="blue"))
    plot.add_item(make.curve(x, np.cos(x), title="cos(x)", color="red"))
    plot.do_autoscale()

    # Show the window
    main.show()

    print(f"Plot type: {PlotType.CURVE}")
    print(f"Dock location: {location}")
    print(f"Number of items: {len(plot.get_items())}")

    main.close()

# %%
# Summary
# -------
#
# The ``DockablePlotWidget`` wraps PlotPy's interactive plots into dock widgets
# that integrate seamlessly with ``SGMXMainWindow`` and any ``QMainWindow``.
#
# - Use ``PlotType.CURVE`` for 1D signal display
# - Use ``PlotType.IMAGE`` for 2D image display
# - Call ``get_plot()`` to access the underlying PlotPy plot for adding items
