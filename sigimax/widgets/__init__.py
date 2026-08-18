# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX widgets
===============

Reusable Qt widgets for SigimaX-derived applications.

Convenience imports
-------------------

The most commonly used widgets are re-exported here for easy access::

    from sigimax.widgets import H5Browser, Wizard, LogViewerWindow

Specialized scientific dialogs (fit, peak detection, baseline, etc.) remain
accessible via their submodule::

    from sigimax.widgets.fitdialog import gaussian_fit
    from sigimax.widgets.signalpeak import SignalPeakDetectionDialog

Submodules
----------

.. autosummary::

    plotdock
    connection
    filedialog
    fileviewer
    fitdialog
    h5browser
    imagebackground
    logviewer
    objectdialog
    signalbaseline
    signalcursor
    signaldeltax
    signalpeak
    splashscreen
    status
    warningerror
    wizard
"""

from sigimax.widgets.connection import ConnectionDialog
from sigimax.widgets.h5browser import H5Browser, H5BrowserDialog
from sigimax.widgets.logviewer import LogViewerWindow
from sigimax.widgets.objectdialog import GetObjectDialog, SimpleObjectTree
from sigimax.widgets.plotdock import (
    CurveStatsToolFunctions,
    DockablePlotWidget,
    SigimaXPlotWidget,
)
from sigimax.widgets.splashscreen import SigimaXSplashScreen, SplashScreenConfig
from sigimax.widgets.status import BaseStatus, ConsoleStatus, MemoryStatus
from sigimax.widgets.warningerror import WarningErrorMessageBox, show_warning_error
from sigimax.widgets.wizard import Wizard, WizardPage

__all__ = [
    "BaseStatus",
    "ConnectionDialog",
    "ConsoleStatus",
    "CurveStatsToolFunctions",
    "DockablePlotWidget",
    "GetObjectDialog",
    "H5Browser",
    "H5BrowserDialog",
    "LogViewerWindow",
    "MemoryStatus",
    "SigimaXPlotWidget",
    "SigimaXSplashScreen",
    "SimpleObjectTree",
    "SplashScreenConfig",
    "WarningErrorMessageBox",
    "Wizard",
    "WizardPage",
    "show_warning_error",
]
